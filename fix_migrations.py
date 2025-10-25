#!/usr/bin/env python
"""
Quick script to fix migration history by directly updating django_migrations table.
This bypasses Django's consistency check.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from django.db import connection

def fix_migrations():
    """Fix the migration history by marking authentication.0001_initial as applied."""
    with connection.cursor() as cursor:
        # Check if authentication.0001_initial is already recorded
        cursor.execute(
            "SELECT COUNT(*) FROM django_migrations WHERE app='authentication' AND name='0001_initial'"
        )
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("✓ Inserting authentication.0001_initial into migration history...")
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                ['authentication', '0001_initial']
            )
            print("✓ Migration history fixed!")
            print("\nNow run: python manage.py migrate")
        else:
            print("✗ authentication.0001_initial is already in migration history.")
            print("The issue might be different. Check your migration state with:")
            print("  python manage.py showmigrations")
    
    return True

if __name__ == '__main__':
    try:
        fix_migrations()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
