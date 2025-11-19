import os
import django
from django.conf import settings
from django.test.utils import setup_test_environment, teardown_test_environment
import pytest

# Configure Django settings before any tests run
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()


@pytest.fixture(scope='session', autouse=True)
def django_test_environment():
    """Set up Django test environment for the entire test session."""
    setup_test_environment()
    yield
    teardown_test_environment()


@pytest.fixture(scope='session', autouse=True)
def configure_timezone():
    """Configure timezone settings for MySQL database."""
    import pymysql
    from django.db import connection
    
    # Force timezone configuration for MySQL
    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET time_zone = '+00:00'")
                cursor.execute("SET sql_mode='STRICT_TRANS_TABLES'")
        except Exception:
            pass  # Ignore if database is not yet available
    
    yield


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests automatically."""
    # Ensure timezone is set for each test in case connection is reset
    from django.db import connection
    if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET time_zone = '+00:00'")
                cursor.execute("SET sql_mode='STRICT_TRANS_TABLES'")
        except Exception:
            pass
    yield
