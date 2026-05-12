"""Clinical quality indicators for Hospital Clínic de Barcelona.

Top-level package re-exports the Metabase connection helpers so callers can do:

    from indicadors_iso import execute_query, execute_query_yearly
"""

from indicadors_iso.connection import (
    METABASE_SILENT_ROW_CAP,
    execute_query,
    execute_query_yearly,
)

__all__ = [
    "METABASE_SILENT_ROW_CAP",
    "execute_query",
    "execute_query_yearly",
]
