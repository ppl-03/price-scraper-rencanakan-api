from django.core.management.base import BaseCommand
from django.db import connection
from scraping_vendor_data.services import DjangoScrapingVendorDataRepository


class Command(BaseCommand):
    help = 'Ensure scraping vendor data table exists, create if it does not'

    def handle(self, *args, **options):
        repository = DjangoScrapingVendorDataRepository()
        
        if repository.table_exists():
            self.stdout.write(
                self.style.SUCCESS('Table "scraping_vendor_data" already exists.')
            )
        else:
            self.stdout.write(
                'Table "scraping_vendor_data" does not exist. Creating...'
            )
            
            try:
                # Import here to avoid circular imports
                from django.core.management import execute_from_command_line
                import sys
                
                # Save current argv
                original_argv = sys.argv
                
                # Run makemigrations
                sys.argv = ['manage.py', 'makemigrations', 'scraping_vendor_data']
                execute_from_command_line(sys.argv)
                
                # Run migrate
                sys.argv = ['manage.py', 'migrate']
                execute_from_command_line(sys.argv)
                
                # Restore original argv
                sys.argv = original_argv
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully created table "scraping_vendor_data".')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to create table: {e}')
                )
                
            # Double check if table now exists
            if repository.table_exists():
                self.stdout.write(
                    self.style.SUCCESS('Table "scraping_vendor_data" is now available.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Table creation may have failed. Please check manually.')
                )