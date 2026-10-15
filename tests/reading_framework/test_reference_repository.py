"""QuestionRepository tests: target dari bank soal, bukan dari transkrip."""

from __future__ import annotations

import json

import pytest

from reading_framework.repository import (
    LocalQuestionRepository,
    QuestionNotFoundError,
)


def _write_bank(tmp_path, records):
    p = tmp_path / "bank.json"
    p.write_text(json.dumps({"questions": records}), encoding="utf-8")
    return p


def test_get_returns_target_text(tmp_path):
    p = _write_bank(tmp_path, [{"question_id": "q1", "target_text": "ibu pergi ke pasar"}])
    repo = LocalQuestionRepository.from_file(p)
    q = repo.get("q1")
    assert q.target_text == "ibu pergi ke pasar"
    assert q.source_type == "question_bank"


def test_missing_question_raises(tmp_path):
    p = _write_bank(tmp_path, [{"question_id": "q1", "target_text": "x"}])
    repo = LocalQuestionRepository.from_file(p)
    with pytest.raises(QuestionNotFoundError):
        repo.get("nope")
    assert repo.exists("q1") is True
    assert repo.exists("nope") is False


def test_inactive_question_not_found(tmp_path):
    p = _write_bank(tmp_path, [{"question_id": "q1", "target_text": "x", "active": False}])
    repo = LocalQuestionRepository.from_file(p)
    assert repo.exists("q1") is False
    with pytest.raises(QuestionNotFoundError):
        repo.get("q1")


def test_list_form_supported(tmp_path):
    p = tmp_path / "bank.json"
    p.write_text(json.dumps([{"question_id": "q1", "target_text": "a"}]), encoding="utf-8")
    repo = LocalQuestionRepository.from_file(p)
    assert repo.list_ids() == ["q1"]
