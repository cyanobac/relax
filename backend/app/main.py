"""FastAPI entry point for the Oura stress extractor web app."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .extractor.ocr_helpers import configure_tesseract
from .routes import router

# Locate the Tesseract binary once at startup (PATH in Docker, Program Files on
# Windows). An explicit path can be forced via TESSERACT_CMD.
configure_tesseract(os.environ.get("TESSERACT_CMD"))

app = FastAPI(title="Oura Stress Extractor", version="0.1.0")

# In dev, the Vite dev server (http://localhost:5173) calls the API directly.
# In prod everything is same-origin behind Caddy, so CORS is a no-op there.
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
