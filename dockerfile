# Use the official Python image as the base image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

# System deps for mysqlclient/psycopg2 and Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
    default-libmysqlclient-dev \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libnspr4 \
    libnss3 \
    libnssutil3 \
    libdbus-1-3 \
    libgio2.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

EXPOSE 8000

# Koyeb provides $PORT. Collect static files at startup, then run Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:${PORT:-8000} price_scraper_rencanakan_api.wsgi:application"]