"""Regression tests terhadap JSON ASR NYATA (out/indo_*.json).

Tujuan:
- memastikan fixture lama tetap dapat dibaca dan strukturnya dipahami;
- merekam temuan audit (metadata segmen berulang) sebagai regresi terkontrol;
- membuktikan transkrip mentah dapat direkonstruksi persis dari segmen.

Fixture ini adalah hasil ASR NYATA dari model base (bukan buatan).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"

REAL_JSONS = sorted(OUT.glob("indo_*.json"))


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.skipif(not REAL_JSONS, reason="no real JSON fixtures present")
@pytest.mark.parametrize("path", REAL_JSONS, ids=lambda p: p.name)
def test_real_json_parses_and_has_segments(path):
    d = _load(path)
    assert "segments" in d
    assert isinstance(d["segments"], list)
    assert d["language"] == "id"


@pytest.mark.skipif(not REAL_JSONS, reason="no real JSON fixtures present")
@pytest.mark.parametrize("path", REAL_JSONS, ids=lambda p: p.name)
def test_raw_text_reconstructable_from_segments(path):
    d = _load(path)
    rebuilt = " ".join(s["text"].strip() for s in d["segments"] if s["text"].strip()).strip()
    assert rebuilt == d["text"].strip()


@pytest.mark.skipif(not REAL_JSONS, reason="no real JSON fixtures present")
@pytest.mark.parametrize("path", REAL_JSONS, ids=lambda p: p.name)
def test_word_timestamps_within_audio_bounds(path):
    d = _load(path)
    duration = d.get("audio_seconds") or 0.0
    for seg in d["segments"]:
        for w in seg.get("words", []):
            assert 0.0 <= w["start"] <= duration + 1.0
            assert w["start"] <= w["end"]
            assert 0.0 <= w["probability"] <= 1.0


@pytest.mark.skipif(not REAL_JSONS, reason="no real JSON fixtures present")
def test_repeated_segment_metadata_is_real_engine_behavior():
    """Rekam temuan audit: metadata segmen dapat identik antar-segmen.

    Ini perilaku upstream faster-whisper (bukan bug pemetaan kita). Test ini
    memastikan kita MENGETAHUI dan tidak 'memperbaiki' data sumber diam-diam.
    """
    d = _load(OUT / "indo_1.json")
    metas = [(s["avg_logprob"], s["no_speech_prob"], s["compression_ratio"])
             for s in d["segments"]]
    # minimal ada dua segmen dengan metadata identik (temuan nyata)
    assert len(metas) != len(set(metas)), "expected repeated metadata finding"


@pytest.mark.skipif(not REAL_JSONS, reason="no real JSON fixtures present")
def test_correct_vs_typo_fixtures_differ():
    correct = _load(OUT / "indo_1-1_correct.json")
    typo = _load(OUT / "indo_1-1_typo.json")
    assert correct["text"].strip() == "ibu pergi ke pasar"
    assert typo["text"].strip() == "ibu pergi ke pasap"
