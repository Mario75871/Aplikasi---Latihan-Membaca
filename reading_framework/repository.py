"""Question repository: sumber teks acuan resmi (target_text).

Batas antarmodul yang jelas antara sumber soal dan engine ASR. ``question_id``
menjadi identitas sumber target untuk workflow website.

Ketentuan:
- target diambil dari penyimpanan soal, BUKAN dari raw transcript;
- target tidak dikoreksi LLM, tidak diganti diam-diam;
- bila soal tidak ditemukan, alignment berstatus not_computed dengan alasan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


class QuestionNotFoundError(LookupError):
    """Soal tidak ditemukan atau statusnya tidak valid."""


@dataclass
class Question:
    question_id: str
    target_text: str
    source_type: str = "question_bank"
    version: str | None = None
    language: str = "id"
    active: bool = True
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class QuestionRepository(Protocol):
    """Antarmuka repository soal (implementasi produksi menyediakan adapter DB)."""

    def get(self, question_id: str) -> Question:  # pragma: no cover - interface
        ...

    def exists(self, question_id: str) -> bool:  # pragma: no cover - interface
        ...


class LocalQuestionRepository:
    """Implementasi lokal: bank soal JSON di disk.

    Format berkas::

        {
          "questions": [
            {"question_id": "q1", "target_text": "...", ...}
          ]
        }

    atau daftar langsung ``[{...}, ...]``.

    Jujur: ini BUKAN database produksi; hanya untuk pengembangan & pengujian.
    """

    source_type = "question_bank"

    def __init__(self, items: list[Question]):
        self._by_id: dict[str, Question] = {q.question_id: q for q in items}

    @classmethod
    def from_file(cls, path: str | Path) -> "LocalQuestionRepository":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = raw["questions"] if isinstance(raw, dict) else raw
        items = [
            Question(
                question_id=str(r["question_id"]),
                target_text=str(r.get("target_text", "")),
                source_type=str(r.get("source_type", "question_bank")),
                version=r.get("version"),
                language=str(r.get("language", "id")),
                active=bool(r.get("active", True)),
                metadata=r.get("metadata", {}) or {},
            )
            for r in records
        ]
        return cls(items)

    def get(self, question_id: str) -> Question:
        q = self._by_id.get(question_id)
        if q is None:
            raise QuestionNotFoundError(f"question not found: {question_id!r}")
        if not q.active:
            raise QuestionNotFoundError(f"question is inactive: {question_id!r}")
        return q

    def exists(self, question_id: str) -> bool:
        q = self._by_id.get(question_id)
        return q is not None and q.active

    def list_ids(self) -> list[str]:
        return sorted(self._by_id)
