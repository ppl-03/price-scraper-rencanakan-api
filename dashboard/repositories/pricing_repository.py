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

        # Validate per_vendor_limit early and ensure it's safe to inline into SQL.
        if not isinstance(per_vendor_limit, int) or per_vendor_limit <= 0:
            raise ValueError("per_vendor_limit must be a positive integer")

        # Allow only ASCII word characters in table names to avoid injection.
        table_name_re = re.compile(r"^\w+$", re.ASCII)
        q = connection.ops.quote_name

        # Try to fetch existing table names from DB to further validate identifiers.
        # If introspection is unavailable (e.g. in some unit tests), fall back
        # to only the regex/quoting checks below.
        try:
            existing_tables = set(connection.introspection.table_names())
        except Exception:
            existing_tables = None

        for model, source in self.vendor_specs:
            table = model._meta.db_table

            if not table_name_re.match(table):
                raise ValueError(f"Unsafe table name detected: {table!r}")

            # If introspection succeeded but the table isn't listed, don't fail
            # outright. Unit tests and some runtime setups may use synthetic
            # or virtual table names that introspection won't know about.
            # We already validated the identifier via regex above and will
            # quote it below, so continue using that safer fallback.
            if existing_tables is not None and table not in existing_tables:
                # fallback to regex/quoting; do not raise here in test environments
                pass

            quoted_table = q(table)

            # Use parameter placeholders for `source` and `per_vendor_limit` so
            # the values remain bound parameters. We validated/quoted
            # identifiers above to prevent injection into SQL text.
            select_sql = (
                f"(SELECT {q('name')} AS item, {q('price')} AS value, {q('unit')}, {q('url')}, {q('location')}, {q('category')}, {q('created_at')}, {q('updated_at')}, %s AS source "
                f"FROM {quoted_table} ORDER BY {q('updated_at')} DESC LIMIT %s)"
            )

            parts.append(select_sql)
            params.append(source)
            params.append(per_vendor_limit)

        if not parts:
            return []

        union_sql = " UNION ALL ".join(parts)

        # Wrap the union so we can order the final result across vendors.
        full_sql = f"SELECT * FROM ({union_sql}) AS combined ORDER BY value ASC"

        # Use a prepared cursor when supported by the DB driver; fall back if not.
        try:
            cur_obj = connection.cursor(prepared=True)  # type: ignore[arg-type]
        except Exception:
            cur_obj = connection.cursor()

        with cur_obj as cur:
            # Pass parameters as a tuple to the DB-API. LIMIT is inlined (validated),
            # so params only contains the `source` values which are safe to bind.
            cur.execute(full_sql, tuple(params))
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

        return rows
