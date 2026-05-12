"""Backward-compat shim — real implementation in indicadors_iso.deliris.run_sql."""
import sys

from indicadors_iso.deliris.run_sql import main

if __name__ == "__main__":
    sys.exit(main())
