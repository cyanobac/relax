"""API routes for the stress extractor web app."""
import base64
from datetime import datetime
from pathlib import Path

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .extractor.core import (
    ExtractionError,
    decode_image,
    extract_from_array,
    validate_dimensions,
)

router = APIRouter(prefix="/api")

MASK_PATH = str(Path(__file__).parent / "extractor" / "mask_scaled.png")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB is plenty for a phone screenshot


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

    try:
        img = decode_image(raw)
        validate_dimensions(img)
        result = extract_from_array(img, MASK_PATH, reference_date)
    except ExtractionError as e:
        # Expected, user-facing problems (bad size, undecodable, no dots).
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001 - surface anything unexpected as 500
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    annotated = result.pop("annotated")
    if include_image:
        ok, buf = cv2.imencode(".png", annotated)
        if ok:
            result["annotated_png"] = base64.b64encode(buf).decode("ascii")

    return result
