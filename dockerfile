# Use the official Python image as the base image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

# System deps for mysqlclient/psycopg2 + Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
    default-libmysqlclient-dev \
    curl \
    wget \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb1 \
    libxcb-dri2-0 \
    libxshmfence1 \
    libxfixes3 \
    libxrender1 \
    libxext6 \
    libxss1 \
    libglib2.0-0 \
    libexpat1 \
    zlib1g \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers in separate layer to avoid issues
RUN python -m playwright install --with-deps webkit

COPY . /app/

EXPOSE 8000

# Memory-optimized Gunicorn configuration for Koyeb deployment
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn --workers 1 --worker-class sync --worker-connections 100 --max-requests 1000 --max-requests-jitter 100 --timeout 120 --keep-alive 2 --preload --bind 0.0.0.0:${PORT:-8000} price_scraper_rencanakan_api.wsgi:application"]