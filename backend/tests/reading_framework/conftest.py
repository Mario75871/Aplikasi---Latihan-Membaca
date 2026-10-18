"""Shared pytest fixtures and configuration.

Unit test TIDAK memuat model Whisper. Integration test (yang butuh model) di
gate dengan marker ``integration`` dan env ``RAW_READING_INTEGRATION=1``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Path ke backend (untuk import reading_framework)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Path ke fixture framework (mandiri di dalam backend).
# Fase A (integrasi #2): fixture dipindahkan ke dalam backend agar `backend/`
# dapat di-deploy & di-test TANPA folder `framework-whisper-2/` di luar.
# Struktur: fixtures/audio/*.wav + fixtures/examples/question_bank/questions.json
ROOT = Path(__file__).resolve().parent / "fixtures"

QUESTION_BANK = ROOT / "examples" / "question_bank" / "questions.json"
AUDIO_DIR = ROOT / "audio"
OUT_DIR = ROOT / "out"


def integration_enabled() -> bool:
    return os.environ.get("RAW_READING_INTEGRATION") == "1"


def pytest_configure(config):
    config.addinivalue_line("markers",
                            "integration: needs the cached Whisper model + real audio")


def pytest_collection_modifyitems(config, items):
    if integration_enabled():
        return
    skip = pytest.mark.skip(reason="integration disabled (set RAW_READING_INTEGRATION=1)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def question_bank_path() -> Path:
    return QUESTION_BANK


@pytest.fixture(autouse=True)
def _chdir_to_framework_root(monkeypatch):
    """Jalankan test framework dari ROOT agar path relatif 'audio/...' ditemukan.

    Test framework asli memakai path relatif terhadap root framework
    (mis. AUDIO = "audio/indo_1-1_correct.wav"). Saat dipindah ke backend,
    CWD berubah sehingga path tidak ditemukan. Fixture ini mengembalikan CWD
    ke ROOT selama test berjalan, tanpa mengubah kode test framework.
    """
    monkeypatch.chdir(ROOT)
    yield


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    return d
