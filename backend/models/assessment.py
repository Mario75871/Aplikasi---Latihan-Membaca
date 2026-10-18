"""Pydantic models — BacaLaras v2.5 (§34).

Kontrak validasi resmi (integrasi #2, keputusan D1: DIPERTAHANKAN).
Catatan v2.5: tidak ada field error pattern / self-correction.
Aturan `null` ≠ `0`: nilai yang tidak dapat dihitung = ``None``, bukan 0.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AdaptiveStatus(str, Enum):
    INTERVENE = "INTERVENE"
    STAY = "STAY"
    PROMOTION_CANDIDATE = "PROMOTION_CANDIDATE"
    PROMOTE = "PROMOTE"


class Competency(str, Enum):
    RETRIEVE = "retrieve"
    INTERPRET = "interpret"
    REFLECT = "reflect"


# ---------- Reading ----------
class ReadingQuestion(BaseModel):
    id: str
    competency: Competency
    prompt: str
    options: list[dict]
    answer_id: str


class ReadingText(BaseModel):
    id: str
    title: str
    content: str
    grade: int = Field(ge=1, le=3)
    complexity: int = Field(ge=1, le=3)
    book_level: str = Field(pattern="^B[1-3]$")  # B1, B2, B3
    word_count: int
    theme: Optional[str] = None
    proper_nouns: list[str] = []  # D5: nama/proper noun per teks
    questions: list[ReadingQuestion] = []


# ---------- Student / Class ----------
class Student(BaseModel):
    id: str
    name: str
    grade: int = Field(ge=1, le=3)
    class_id: str


# ---------- Word score (§13.2) ----------
class WordScore(BaseModel):
    position: int
    reference_word: Optional[str] = None  # framework alignment
    transcript_word: Optional[str] = None
    confidence: Optional[float] = None  # model_probability dari framework
    attempted: bool  # D1: dicoba dibaca (match/substitution)
    is_correct: bool
    is_proper_noun: bool = False
    reason: str = ""  # D10: traceability
    review_reasons: list[str] = []  # dari framework
    ts_start: Optional[float] = None
    ts_end: Optional[float] = None


# ---------- Comprehension (§17) ----------
class ComprehensionResult(BaseModel):
    """Skor pemahaman. ``None`` = kompetensi tidak dijawab/tak dapat dihitung."""

    retrieve: Optional[float] = Field(default=None, ge=0, le=100)
    interpret: Optional[float] = Field(default=None, ge=0, le=100)
    reflect: Optional[float] = Field(default=None, ge=0, le=100)


class ComprehensionAnswer(BaseModel):
    question_id: str
    answer_id: str


# ---------- Assessment ----------
class AssessmentCreate(BaseModel):
    student_id: str
    reading_id: str


class AssessmentResult(BaseModel):
    id: str
    student_id: str
    # null ≠ 0: None bila tidak dapat dihitung (mis. durasi tak tersedia).
    wcpm: Optional[float] = None
    accuracy: Optional[float] = None
    correct_words: int
    incorrect_words: int
    total_words_read: int  # D1: denominator Accuracy
    comprehension: ComprehensionResult
    status: AdaptiveStatus
    recommendation: str
    next_reading_level: int = Field(ge=1, le=3)
    rules_fired: list[dict] = []
    word_scores: list[WordScore] = []
    framework_result: Optional[dict] = None  # JSON audit dari framework
    is_demo_fallback: bool = False  # mode demo
