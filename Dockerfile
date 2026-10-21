FROM python:3.11-slim

# Install system dependencies: Tesseract OCR, Poppler (pdftoppm), and common image libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY pyproject.toml .

# Install Python dependencies and pip tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code and configs
COPY src/ ./src/
COPY configs/ ./configs/

# Reinstall docextract in editable or clean mode
RUN pip install --no-cache-dir -e .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    DOCEXTRACT_API_KEY=dev-key-change-in-prod

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "docextract.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
