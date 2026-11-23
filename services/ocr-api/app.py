"""
ocr-api — OCR for scanned vendor documents (images or image-only PDFs).

POST /ocr     multipart file (png/jpg/tiff/pdf) -> {"text", "pages"}
GET  /health
"""

import io
import os

import pytesseract
from fastapi import FastAPI, File, HTTPException, UploadFile
from pdf2image import convert_from_bytes
from PIL import Image

OCR_LANG = os.getenv("OCR_LANG", "spa+eng")
MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
PDF_DPI = int(os.getenv("PDF_DPI", "300"))

app = FastAPI(title="ocr-api", version="1.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "lang": OCR_LANG}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(413, "File too large")

    is_pdf = contents[:4] == b"%PDF" or (file.filename or "").lower().endswith(".pdf")
    try:
        if is_pdf:
            pages = convert_from_bytes(contents, dpi=PDF_DPI)
        else:
            pages = [Image.open(io.BytesIO(contents))]
    except Exception as exc:
        raise HTTPException(400, f"Unsupported or corrupt file: {exc}") from exc

    texts = [pytesseract.image_to_string(page, lang=OCR_LANG) for page in pages]
    return {"text": "\n\f\n".join(texts), "pages": len(pages)}
