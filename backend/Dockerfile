# Backend: FastAPI + OpenCV + Tesseract OCR
FROM python:3.12-slim

# Tesseract is a system package (pytesseract just shells out to it).
# libglib2.0-0 is needed by opencv-python-headless at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
