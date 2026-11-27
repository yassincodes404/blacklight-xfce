#!/usr/bin/env python3
"""CLI entry point for the shared Galinia Firefox memory preset implementation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'home/.local/share/galinia'))
from memory_preset import *

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit('Galinia Firefox memory: ' + str(error)) from None
