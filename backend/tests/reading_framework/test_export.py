"""Export tests: penulisan raw transcript TXT + JSON + anti-overwrite."""

from __future__ import annotations

import json

import pytest

from reading_framework.transcript_writer import (
    OutputWriteError,
    read_json,
    write_json,
    write_raw_transcript_text,
)


def test_write_raw_transcript_only_text(tmp_path):
    p = write_raw_transcript_text("ibu pergi ke pasap", tmp_path / "transcript_raw.txt")
    assert p.read_text(encoding="utf-8") == "ibu pergi ke pasap\n"


def test_raw_transcript_no_metadata(tmp_path):
    p = write_raw_transcript_text("halo dunia", tmp_path / "t.txt")
    content = p.read_text(encoding="utf-8")
    assert "WER" not in content
    assert "target" not in content


def test_anti_overwrite_default(tmp_path):
    path = tmp_path / "t.txt"
    write_raw_transcript_text("first", path)
    with pytest.raises(OutputWriteError):
        write_raw_transcript_text("second", path)
    assert path.read_text(encoding="utf-8") == "first\n"


def test_overwrite_allowed(tmp_path):
    path = tmp_path / "t.txt"
    write_raw_transcript_text("first", path)
    write_raw_transcript_text("second", path, overwrite=True)
    assert path.read_text(encoding="utf-8") == "second\n"


def test_failed_asr_writes_marker_not_fake_transcript(tmp_path):
    p = write_raw_transcript_text("", tmp_path / "t.txt", failed_error="boom")
    content = p.read_text(encoding="utf-8")
    assert "ASR FAILED" in content
    assert "boom" in content


def test_write_and_read_json(tmp_path):
    payload = {"schema_version": "1.0.0", "text": "halo dunia"}
    p = write_json(payload, tmp_path / "r.json")
    assert read_json(p) == payload


def test_utf8_preserved(tmp_path):
    p = write_json({"t": "terima kasih"}, tmp_path / "r.json")
    assert "terima kasih" in p.read_text(encoding="utf-8")
    assert json.loads(p.read_text(encoding="utf-8"))["t"] == "terima kasih"
