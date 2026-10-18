#!/usr/bin/env bash
# Anti-drift: pastikan backend/reading_framework/ tetap identik dengan sumber
# framework-whisper-2/reading_framework/ (integrasi #2, Fase D — opsional).
#
# Bila berbeda (di luar __pycache__ / .DS_Store), skrip GAGAL — tanda vendored
# perlu disinkronkan ulang, atau framework sumber berubah tanpa ditinjau.
#
# Pakai: bash backend/scripts/check_framework_drift.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/framework-whisper-2/reading_framework"
DST="$REPO_ROOT/backend/reading_framework"

if [[ ! -d "$SRC" ]]; then
  echo "[skip] Folder sumber tidak ada: $SRC"
  echo "       (backend mandiri; drift check hanya bermakna bila sumber tersedia.)"
  exit 0
fi

if [[ ! -d "$DST" ]]; then
  echo "[FAIL] Folder vendored tidak ada: $DST" >&2
  exit 1
fi

echo "Membandingkan:"
echo "  SRC: $SRC"
echo "  DST: $DST"

# Bandingkan, abaikan artefak non-sumber.
DIFF_OUT="$(diff -rq "$SRC" "$DST" \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' || true)"

if [[ -n "$DIFF_OUT" ]]; then
  echo "[FAIL] Ditemukan perbedaan (drift) antara sumber dan vendored:" >&2
  echo "$DIFF_OUT" >&2
  echo >&2
  echo "Tindakan: sinkronkan ulang backend/reading_framework/ dari sumber," >&2
  echo "atau tinjau perubahan framework sebelum melanjutkan." >&2
  exit 1
fi

echo "[OK] Tidak ada drift — backend/reading_framework/ identik dengan sumber."
