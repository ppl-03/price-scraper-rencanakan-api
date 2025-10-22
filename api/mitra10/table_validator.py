from django.db import connection
from django.conf import settings


class Mitra10TableValidator:
    """Validator for ensuring Mitra10 database table existence and schema integrity."""

    def __init__(self):
        self.db_engine = settings.DATABASES["default"]["ENGINE"]
        self.table_name = "mitra10_products"

    # =========================
    # Internal Query Helpers
    # =========================
    def _run_query(self, query):
        """Executes a SQL query and returns all results."""
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def _get_query(self, action: str) -> str:
        """Generates the correct SQL query based on DB engine and requested action."""
        if "sqlite" in self.db_engine:
            return (
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table_name}'"
                if action == "exists"
                else f"PRAGMA table_info({self.table_name})"
            )
        elif "mysql" in self.db_engine:
            return (
                f"SHOW TABLES LIKE '{self.table_name}'"
                if action == "exists"
                else f"DESCRIBE {self.table_name}"
            )
        raise NotImplementedError(f"Unsupported database engine: {self.db_engine}")

    # =========================
    # Public Validation Methods
    # =========================
    def check_table_exists(self) -> bool:
        """Checks if the mitra10_products table exists in the current database."""
        result = self._run_query(self._get_query("exists"))
        return bool(result)

    def get_table_schema(self):
        """Retrieves structured table schema details for mitra10_products."""
        columns = self._run_query(self._get_query("schema"))
        if not columns:
            return {}

        if "sqlite" in self.db_engine:
            return {
                col[1]: {
                    "type": col[2],
                    "not_null": bool(col[3]),
                    "default": col[4],
                    "primary_key": bool(col[5]),
                }
                for col in columns
            }

        # MySQL format
        return {
            col[0]: {
                "type": col[1],
                "not_null": col[2] == "NO",
                "default": col[4],
                "primary_key": col[3] == "PRI",
            }
            for col in columns
        }

    def validate_schema(self) -> bool:
        """Verifies that the Mitra10 table exists and includes required columns."""
        if not self.check_table_exists():
            return False

        schema = self.get_table_schema()
        required_cols = {"id", "name", "price", "url", "unit", "created_at", "updated_at"}
        return required_cols.issubset(schema.keys())
