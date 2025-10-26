#!/usr/bin/env python
"""
Script to drop all tables from the MySQL database and reset for fresh migrations.
⚠️ WARNING: This will DELETE ALL DATA in your database!
"""
import os
import django
import sys
import re
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_scraper_rencanakan_api.settings')
django.setup()

from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)

# conservative table name validation: allow letters, numbers, underscore, dollar, and hyphen
_TABLE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-$]+$")

def drop_all_tables():
    """Drop all tables in the database."""
    db_name = settings.DATABASES['default']['NAME']

    with connection.cursor() as cursor:
        # Disable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # Prefer using Django's introspection which avoids formatting SQL ourselves
        try:
            tables = connection.introspection.table_names()
        except Exception:
            # Fallback to a parameterized information_schema query (safe against injection)
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s;",
                [db_name],
            )
            tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            print("✓ No tables found in database.")
            # Re-enable foreign key checks before returning
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            return

        print(f"Found {len(tables)} tables to drop:")
        for table_name in tables:
            # table_name may be a tuple from some fetch implementations; normalize
            if isinstance(table_name, (list, tuple)):
                table_name = table_name[0]

            # Basic sanity check: only allow well-formed table names
            if not isinstance(table_name, str) or not _TABLE_NAME_RE.match(table_name):
                logger.warning(f"Skipping suspicious table name: {table_name!r}")
                continue

            print(f"  - Dropping {table_name}...")

            # Use connection.ops.quote_name to safely quote the identifier for the backend.
            # We validated `table_name` against _TABLE_NAME_RE above, so this identifier
            # is safe to include in an identifier position. Build the query by
            # concatenation from the quoted identifier (not user input) and execute.
            quoted = connection.ops.quote_name(table_name)
            query = "DROP TABLE IF EXISTS " + quoted + ";"  # NOSONAR - safe: validated table_name + quote_name
            cursor.execute(query)

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
