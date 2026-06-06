"""API routes for the stress extractor web app."""
import asyncio
import base64
import logging
import os
from datetime import datetime
from pathlib import Path

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from .extractor.core import (
    ExtractionError,
    decode_image,
    extract_from_array,
    validate_dimensions,
)

logger = logging.getLogger("oura_extractor")

router = APIRouter(prefix="/api")

MASK_PATH = str(Path(__file__).parent / "extractor" / "mask_scaled.png")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB is plenty for a phone screenshot

# OCR is CPU-bound and synchronous; cap how many run at once so a burst of
# uploads can't pin every core (the public box has no auth in front of it).
_MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_EXTRACTIONS", "2"))
_extract_semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

# Bound the waiting room too: every queued request holds its uploaded bytes and
# a connection in memory, so an unbounded queue turns CPU pressure into an OOM.
# Allow a few to wait for a free slot; reject the rest fast with 503 rather than
# letting the queue grow without limit. asyncio is single-threaded, so the
# check-then-increment below is atomic as long as no `await` sits between them.
_MAX_INFLIGHT = int(os.environ.get("MAX_INFLIGHT_EXTRACTIONS", "6"))
_inflight = 0  # running + waiting


def _run_pipeline(raw: bytes, reference_date, include_image: bool) -> dict:
    """Synchronous decode → extract → encode, run off the event loop.

    Lets ExtractionError (and anything unexpected) propagate to the caller for
    HTTP mapping; does no error handling of its own.
    """
    img = decode_image(raw)
    validate_dimensions(img)
    result = extract_from_array(img, MASK_PATH, reference_date)

    annotated = result.pop("annotated")
    if include_image:
        ok, buf = cv2.imencode(".png", annotated)
        if ok:
            result["annotated_png"] = base64.b64encode(buf).decode("ascii")
    return result


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/extract")
async def extract(
    file: UploadFile = File(...),
    date: str = Form(...),
    include_image: bool = Form(False),
):
    """Extract stress points from an uploaded Oura screenshot.

    Form fields:
        file:           the screenshot (PNG/JPEG, 640x1136).
        date:           the day the chart represents, YYYY-MM-DD.
        include_image:  if true, return the annotated chart as a base64 PNG.
    """
    try:
        reference_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Empty upload")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    # Shed load before committing memory: if the running+waiting count is already
    # at the limit, reject fast instead of growing the queue. (Atomic in asyncio:
    # no `await` between the check and the increment.)
    global _inflight
    if _inflight >= _MAX_INFLIGHT:
        raise HTTPException(
            status_code=503,
            detail="Server busy, please try again in a minute.",
            headers={"Retry-After": "60"},
        )
    _inflight += 1
    try:
        # Run the heavy, blocking OCR pipeline in a worker thread so it doesn't
        # freeze the event loop, and gate concurrency so a flood can't exhaust CPU.
        async with _extract_semaphore:
            try:
                return await run_in_threadpool(
                    _run_pipeline, raw, reference_date, include_image
                )
            except ExtractionError as e:
                # Expected, user-facing problems (bad size, undecodable, no dots).
                raise HTTPException(status_code=422, detail=str(e))
            except Exception:  # noqa: BLE001 - surface anything unexpected as 500
                # Log full detail server-side; never leak internals to the client.
                logger.exception("Extraction failed")
                raise HTTPException(
                    status_code=500, detail="Extraction failed. Please try again."
                )
    finally:
        _inflight -= 1
