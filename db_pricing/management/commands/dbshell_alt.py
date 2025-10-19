import sys
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Interactive database shell using Django connection (alternative to dbshell)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query', '-q',
            help='Execute a single query and exit',
        )

    def handle(self, *args, **options):
        if options['query']:
            # Execute single query
            self.execute_query(options['query'])
        else:
            # Interactive mode
            self.interactive_shell()

    def execute_query(self, query):
        """Execute a single query and display results"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                
                # Handle different query types
                if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                    results = cursor.fetchall()
                    if results:
                        # Get column names
                        columns = [desc[0] for desc in cursor.description]
                        
                        # Print headers
                        self.stdout.write(" | ".join(columns))
                        self.stdout.write("-" * (len(" | ".join(columns))))
                        
                        # Print rows
                        for row in results:
                            self.stdout.write(" | ".join(str(cell) if cell is not None else 'NULL' for cell in row))
                    else:
                        self.stdout.write("Empty set")
                else:
                    # For INSERT, UPDATE, DELETE, etc.
                    affected_rows = cursor.rowcount
                    self.stdout.write(self.style.SUCCESS(f"Query executed successfully. Affected rows: {affected_rows}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))

    def interactive_shell(self):
        """Interactive database shell"""
        db_settings = settings.DATABASES['default']
        self.stdout.write(self.style.SUCCESS(
            f"Interactive MySQL shell for {db_settings['NAME']} at {db_settings['HOST']}"
        ))
        self.stdout.write("Type 'help' for help, 'quit' or 'exit' to quit")
        self.stdout.write("-" * 50)

        while True:
            try:
                # Get input
                query = input("mysql> ").strip()
                
                if not query:
                    continue
                    
                if query.lower() in ['quit', 'exit', 'q']:
                    self.stdout.write("Goodbye!")
                    break
                    
                if query.lower() == 'help':
                    self.show_help()
                    continue
                
                # Execute the query
                self.execute_query(query)
                
            except KeyboardInterrupt:
                self.stdout.write("\n\nUse 'quit' or 'exit' to quit")
                continue
            except EOFError:
                self.stdout.write("\nGoodbye!")
                break

    def show_help(self):
        """Show help information"""
        help_text = """
Available commands:
  help          - Show this help
  quit, exit, q - Exit the shell
  
MySQL commands:
  SHOW TABLES;                    - List all tables
  DESCRIBE table_name;            - Show table structure  
  SELECT * FROM table_name;       - Query data
  SHOW CREATE TABLE table_name;   - Show table creation SQL
  
Examples:
  mysql> SHOW TABLES;
  mysql> SELECT * FROM users LIMIT 5;
  mysql> DESCRIBE item_prices;
        """
        self.stdout.write(help_text)