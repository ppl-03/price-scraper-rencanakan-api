# Price Scraper Rencanakan API

[![CI CD](https://github.com/ppl-03/price-scraper-rencanakan-api/actions/workflows/django.yml/badge.svg)](https://github.com/ppl-03/price-scraper-rencanakan-api/actions/workflows/django.yml)
![Coverage](https://raw.githubusercontent.com/ppl-03/price-scraper-rencanakan-api/refs/heads/main/coverage.svg)

A Django-based API for scraping and managing product prices from various vendors.

## Features

- Multi-vendor price scraping (DepoBangunan, Gemilang, Juragan Material, Mitra10, Tokopedia)
- Price anomaly detection and monitoring
- Auto-categorization service
- Government wage data integration
- REST API endpoints
- Admin dashboard
- Automated testing and coverage reporting

## Setup

### Prerequisites

- Python 3.13
- MySQL 8.0
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ppl-03/price-scraper-rencanakan-api.git
cd price-scraper-rencanakan-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a `.env` file):
```
SECRET_KEY=your-secret-key
DB_ENGINE=django.db.backends.mysql
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Run the development server:
```bash
python manage.py runserver
```

## Testing

Run tests with coverage:
```bash
python -m coverage run --source='.' manage.py test
python -m coverage report
```

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:
- Automated testing on push and pull requests
- Coverage reporting with Codecov
- Coverage badge generation
