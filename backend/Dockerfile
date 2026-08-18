FROM python:3.12-slim

# Ghostscript is required by camelot for PDF table extraction (FR-2.7).
# tesseract-ocr + friends are required only when OCR_ENABLED=true (FR-2.8).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    tesseract-ocr \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir -e .

COPY app ./app
COPY tests ./tests

RUN mkdir -p /storage/uploads
VOLUME ["/storage/uploads"]

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
