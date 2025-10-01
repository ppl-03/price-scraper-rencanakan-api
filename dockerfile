# Use the official Python image as the base image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEPLOYMENT_ENV=production

WORKDIR /app

COPY requirements.txt /app/

# System deps for mysqlclient/psycopg2 + Playwright/WebKit (optimized for memory)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
    default-libmysqlclient-dev \
    curl \
    wget \
    ca-certificates \
    # WebKit specific dependencies (lighter than Chromium)
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libglib2.0-0 \
    libexpat1 \
    zlib1g \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install only WebKit browser (much lighter than Chromium - saves ~200MB)
RUN python -m playwright install webkit

COPY . /app/

EXPOSE 8000

# Highly optimized Gunicorn configuration for Koyeb with WebKit
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn --workers 1 --worker-class sync --worker-connections 50 --max-requests 500 --max-requests-jitter 50 --timeout 180 --keep-alive 2 --preload --bind 0.0.0.0:${PORT:-8000} price_scraper_rencanakan_api.wsgi:application"]