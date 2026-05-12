"""Backward-compat shim — real implementation in indicadors_iso.dynamic_forms.run_queries."""
import sys

from indicadors_iso.dynamic_forms.run_queries import main

if __name__ == "__main__":
    sys.exit(main())
