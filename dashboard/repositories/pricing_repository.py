from typing import List, Optional, Dict, Tuple
import re

from django.db import connection
from django.db import models

class PricingRepository:
    """Repository that fetches vendor pricing by combining vendor tables.
    This repository constructs a single SQL query that unions per-vendor
    recent rows (LIMIT per vendor) and returns a combined, ordered list.
    Note: it assumes vendor models share a common column set: `name`,
    `price`, `unit`, `url`, `location`, `category`, `created_at`, `updated_at`.
    """
    def __init__(self, vendor_specs: List[Tuple[models.Model, str]]):
        # vendor_specs is a list of (ModelClass, human_readable_source_name)
        self.vendor_specs = vendor_specs
    def fetch_all(self, per_vendor_limit: int = 100) -> List[Dict]:
        """Return combined rows from all vendor tables.
        This simplified variant does not support text search; it pulls the most
        recent `per_vendor_limit` rows from each vendor table and returns a
        combined list ordered by `value`.
        """
        parts: List[str] = []
        params: List = []
        for model, source in self.vendor_specs:
            table = model._meta.db_table

            # Validate table name to prevent injection; only allow alphanumerics and underscore.
            # This protects against untrusted `db_table` values and ensures quoting is safe.
            if not re.match(r"^\w+$", table):
                raise ValueError(f"Unsafe table name detected: {table!r}")

            # Quote the table name using the backend's quoting rule (adds backticks/quotes).
            quoted_table = connection.ops.quote_name(table)

            # Select columns and add a literal source column. No WHERE clause.
            # Use parameter placeholders for user-controlled values (source, limit).
            select_sql = (
                f"(SELECT `name` AS item, `price` AS value, `unit`, `url`, `location`, `category`, `created_at`, `updated_at`, %s AS source "
                f"FROM {quoted_table} ORDER BY `updated_at` DESC LIMIT %s)"
            )

            parts.append(select_sql)
            params.append(source)
            params.append(per_vendor_limit)
        if not parts:
            return []
        union_sql = " UNION ALL ".join(parts)
        # Wrap the union so we can order the final result across vendors.
        full_sql = f"SELECT * FROM ({union_sql}) AS combined ORDER BY value ASC"


        cursor_obj = None
        try:

            cursor_obj = connection.cursor(prepared=True)  # type: ignore[arg-type]
        except TypeError:
            cursor_obj = connection.cursor()

        # Ensure params are passed as a tuple to DB-API execute (safer and standard).
        exec_params = tuple(params)

        with cursor_obj as cur:
            cur.execute(full_sql, exec_params)
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows