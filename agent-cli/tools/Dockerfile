# Dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y poppler-utils qpdf tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
RUN pip install pypdf pdfplumber reportlab pytesseract pdf2image pypandoc
