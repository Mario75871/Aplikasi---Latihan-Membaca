"""CLI tests: --help, schema, dan validasi argumen (tanpa model)."""

from __future__ import annotations

import json

import pytest

from reading_framework.cli import build_parser, main


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    assert "transcribe" in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_schema_command(capsys):
    assert main(["schema"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["title"] == "ReadingResultSchema"


def test_transcribe_missing_audio_returns_2(tmp_path, capsys):
    code = main(["transcribe", "--audio", str(tmp_path / "nope.wav")])
    assert code == 2


def test_question_id_requires_bank(tmp_path, capsys):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF0000")
    code = main(["transcribe", "--audio", str(audio), "--question-id", "q1"])
    assert code == 2
    assert "question-bank" in capsys.readouterr().err


def test_missing_reference_file_returns_1(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF0000")
    code = main(["transcribe", "--audio", str(audio),
                 "--reference-file", str(tmp_path / "missing.txt")])
    assert code == 1


def test_parser_defaults():
    args = build_parser().parse_args(["transcribe", "--audio", "x.wav"])
    assert args.profile == "raw_reading"
    assert args.model == "base"
    assert args.format == "txt,json"
