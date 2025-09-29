from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Test database connection and run basic queries'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Test connection
            self.stdout.write("Testing database connection...")
            
            # Show tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            self.stdout.write(self.style.SUCCESS("Database connection successful!"))
            self.stdout.write(f"Found {len(tables)} tables:")
            
            for table in tables:
                self.stdout.write(f"  - {table[0]}")
            
            # Get database info
            cursor.execute("SELECT DATABASE() as db_name")
            db_info = cursor.fetchone()
            self.stdout.write(f"Current database: {db_info[0]}")
            
            cursor.execute("SELECT VERSION() as version")
            version_info = cursor.fetchone()
            self.stdout.write(f"MySQL version: {version_info[0]}")