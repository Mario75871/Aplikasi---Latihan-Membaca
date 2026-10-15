"""Seed runner — validasi seed data.

Jalankan: python -m seed.validate
"""
from __future__ import annotations

import sys

from seed.reading_texts import READING_TEXTS
from seed.validator import validate_all


def main() -> int:
    print(f"Validasi {len(READING_TEXTS)} teks bacaan...")
    errors = validate_all(READING_TEXTS)
    if errors:
        print(f"[GAGAL] Ditemukan {len(errors)} error:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("[OK] Semua teks valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
