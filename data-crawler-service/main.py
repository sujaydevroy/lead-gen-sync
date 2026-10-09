"""Entry point kept for convenience: same as `python -m crawler ...` (see README.md)."""

import sys

from crawler.cli import main

if __name__ == "__main__":
    sys.exit(main())
