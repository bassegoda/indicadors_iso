"""pytest configuration for the indicadors_iso test suite.

Real DB-touching tests (e.g. ``test_metabase_row_cap``) require a working
Metabase ``.env`` and are therefore not auto-collected — run them
explicitly with ``python tests/test_metabase_row_cap.py``.
"""
