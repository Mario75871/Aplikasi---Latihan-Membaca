"""Normalisasi ejaan bahasa Indonesia (OPSIONAL, setelah ASR).

Modul ini adalah tahap TERPISAH setelah transkripsi mentah. Ia TIDAK pernah
mengubah ``raw_text`` dan TIDAK pernah menggantikan bukti ASR.

Prinsip yang ditegakkan:

- Hanya kata dengan aturan yang sudah diverifikasi (``source`` terisi) yang
  diubah. Kata tak dikenal TIDAK PERNAH diubah otomatis.
- Pencocokan bersifat whole-token, case-preserving, dan tidak menyentuh tanda
  baca. ``computer`` (kata berdiri sendiri) dipetakan; ``komputernya`` bukan.
- Setiap perubahan dicatat sebagai pasangan ``original`` dan ``normalized``
  beserta ``rule_id`` dan ``reason``.
- Hasil normalisasi adalah *kandidat representasi pembanding*, BUKAN transkrip
  mentah, dan BUKAN bukti pasti bahwa anak membaca dengan benar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SPELLING_NORMALIZATION_PROFILE_ID = "id_spelling_v1"

#: Pemisah token: huruf/angka + apostrof internal dipertahankan sebagai satu
#: token. Tanda baca lain tetap berada di posisinya (tidak diubah).
_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÿ\u2018\u2019']+")


@dataclass(frozen=True)
class SpellingRule:
    """Satu aturan koreksi ejaan yang sudah diverifikasi.

    ``source`` wajib terisi untuk menegaskan bahwa aturan punya dasar yang
    jelas (mis. KBBI). Aturan tanpa ``source`` dianggap belum terverifikasi dan
    sebaiknya tidak diaktifkan.
    """

    rule_id: str
    original: str
    normalized: str
    reason: str
    source: str
    enabled: bool = True

    def matches(self, token: str) -> bool:
        """Cocokkan whole-token, case-insensitive, tanpa mengubah case asli."""
        return token.casefold() == self.original.casefold()

    def apply(self, token: str) -> str:
        """Terapkan koreksi sambil mempertahankan pola huruf besar/kecil."""
        if token.isupper():
            return self.normalized.upper()
        if token[:1].isupper():
            return self.normalized[:1].upper() + self.normalized[1:]
        return self.normalized


#: Aturan yang DIKURASI dan diverifikasi. Sengaja minimal: hanya bentukan yang
#: dasarnya jelas (KBBI). Jangan menambah tebakan.
#:
#: - ``computer`` -> ``komputer``: bentuk Inggris yang kadang muncul dari model
#:   untuk kata baku Indonesia "komputer" (KBBI). Kasus nyata: audio
#:   ``tes_14_10_26_6.wav`` (target "komputer diperbaiki di jakarta").
CURATED_RULES: tuple[SpellingRule, ...] = (
    SpellingRule(
        rule_id="id_computer_komputer",
        original="computer",
        normalized="komputer",
        reason="bentuk Inggris; ejaan baku Indonesia adalah 'komputer'",
        source="KBBI Daring (lema: komputer)",
    ),
)


@dataclass
class SpellingChange:
    """Satu perubahan ejaan yang dapat diaudit."""

    original: str
    normalized: str
    rule_id: str
    reason: str
    source: str
    position: int


@dataclass
class SpellingNormalizationResult:
    """Hasil normalisasi ejaan + daftar perubahan.

    ``text`` adalah representasi pembanding — BUKAN transkrip mentah.
    """

    text: str
    changes: list[SpellingChange] = field(default_factory=list)
    profile_id: str = SPELLING_NORMALIZATION_PROFILE_ID
    enabled: bool = True


def _active_rules(rules: tuple[SpellingRule, ...] | list[SpellingRule]
                  ) -> list[SpellingRule]:
    return [r for r in rules if r.enabled]


def normalize_spelling(
    text: str | None,
    rules: tuple[SpellingRule, ...] | list[SpellingRule] | None = None,
    *,
    enabled: bool = True,
) -> SpellingNormalizationResult:
    """Terapkan aturan ejaan terverifikasi pada ``text`` (representasi baru).

    - Tidak pernah memodifikasi input secara in-place.
    - Hanya token yang cocok aturan aktif yang diubah.
    - Bila ``enabled`` False, kembalikan teks apa adanya tanpa perubahan.
    """
    if text is None:
        text = ""
    rules = CURATED_RULES if rules is None else rules

    if not enabled:
        return SpellingNormalizationResult(text=text, changes=[], enabled=False)

    active = _active_rules(rules)
    if not active:
        return SpellingNormalizationResult(text=text, changes=[])

    changes: list[SpellingChange] = []

    def _replace(match: re.Match) -> str:
        token = match.group(0)
        for rule in active:
            if rule.matches(token):
                replacement = rule.apply(token)
                if replacement != token:
                    changes.append(SpellingChange(
                        original=token,
                        normalized=replacement,
                        rule_id=rule.rule_id,
                        reason=rule.reason,
                        source=rule.source,
                        position=match.start(),
                    ))
                    return replacement
        return token

    normalized_text = _TOKEN_RE.sub(_replace, text)
    return SpellingNormalizationResult(text=normalized_text, changes=changes)
