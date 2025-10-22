#!/usr/bin/env python
"""
Script to drop all tables from the MySQL database and reset for fresh migrations.
⚠️ WARNING: This will DELETE ALL DATA in your database!
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from django.db import connection
from django.conf import settings

def drop_all_tables():
    """Drop all tables in the database."""
    db_name = settings.DATABASES['default']['NAME']
    
    with connection.cursor() as cursor:
        # Disable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        # Get all tables
        cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{db_name}';")
        tables = cursor.fetchall()
        
        if not tables:
            print("✓ No tables found in database.")
            return
        
        print(f"Found {len(tables)} tables to drop:")
        for table in tables:
            table_name = table[0]
            print(f"  - Dropping {table_name}...")
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        print(f"\n✓ Successfully dropped all {len(tables)} tables!")
        print("\nNext steps:")
        print("  1. Run: python manage.py migrate")
        print("  2. Run: python manage.py createsuperuser")

if __name__ == '__main__':
    response = input("⚠️  WARNING: This will DELETE ALL DATA in your database!\nAre you sure? Type 'yes' to continue: ")
    
    if response.lower() == 'yes':
        try:
            drop_all_tables()
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
    else:
        print("Aborted. No changes made.")
