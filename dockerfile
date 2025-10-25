# Use the official Python image as the base image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

# System deps for mysqlclient/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
    default-libmysqlclient-dev \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install && playwright install-deps

# Clean up to reduce image size
RUN apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

EXPOSE 8000

# Collect static files at startup, then run Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn price_scraper_rencanakan_api.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers=4 --threads=2 --worker-class=sync --timeout=120"]