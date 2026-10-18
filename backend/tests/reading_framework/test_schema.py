"""Schema tests: kontrak 1.0.0 validasi + JSON Schema export."""

from __future__ import annotations

import json

from reading_framework.config import SCHEMA_VERSION
from reading_framework.schemas import ReadingResultSchema, json_schema


def _minimal_result(**overrides):
    base = {
        "job": {"job_id": "job-x", "status": "completed", "question_id": None},
    }
    base.update(overrides)
    return base


def test_schema_version_constant():
    assert SCHEMA_VERSION == "1.0.0"


def test_minimal_result_validates_and_defaults():
    schema = ReadingResultSchema(**_minimal_result())
    d = schema.model_dump()
    assert d["schema_version"] == "1.0.0"
    # default: null / false, bukan 0 / array pengisi
    assert d["alignment"]["status"] == "not_computed"
    assert d["alignment"]["wer"] is None
    assert d["reference"]["used_during_asr"] is False
    assert d["assessment"]["reading_correctness_confirmed"] is False
    assert d["assessment"]["pronunciation_verified"] is False
    assert d["errors"] == []
    assert d["warnings"] == []


def test_extra_field_forbidden():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ReadingResultSchema(**_minimal_result(bogus_field=1))


def test_operation_enum_enforced():
    import pytest
    from pydantic import ValidationError
    bad = _minimal_result()
    bad["alignment"] = {"status": "computed", "words": [
        {"position": 0, "operation": "wrong", "reference_word": "a"}]}
    with pytest.raises(ValidationError):
        ReadingResultSchema(**bad)


def test_json_schema_export_is_serializable():
    s = json_schema()
    assert s["title"] == "ReadingResultSchema"
    json.dumps(s)  # harus bisa diserialisasi ke JSON


def test_alignment_status_enum():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ReadingResultSchema(**_minimal_result(alignment={"status": "bogus"}))
