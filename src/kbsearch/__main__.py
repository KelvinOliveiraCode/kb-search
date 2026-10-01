"""Permite executar como ``python -m kbsearch``.

Enables running as ``python -m kbsearch``.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())