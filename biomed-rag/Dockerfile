FROM python:3.11-slim

WORKDIR /app

# Set UTF-8 locale to fix encoding issues
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# Install system dependencies for Selenium, OCR, and PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    libtesseract-dev \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate and install locale
RUN locale-gen C.UTF-8
RUN update-locale LANG=C.UTF-8

# Set Chrome path for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
ENV PIP_DEFAULT_TIMEOUT=300
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    pip install --retries 10 --timeout 300 -r requirements.txt

# Copy application code
COPY . .

# Create local storage directory
RUN mkdir -p local_storage

# Expose port
EXPOSE 8000

# Run the application with UTF-8 encoding
CMD ["python", "-c", "import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8'); exec(open('main.py').read())"]


