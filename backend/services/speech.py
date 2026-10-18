"""Model #1 — Adapter Reading Framework (Fase 1A).

Wrapper tipis untuk reading_framework. BacaLaras memanggil transcribe_reading()
dari framework, lalu memakai hasilnya untuk penilaian kata (Model #2) di scoring.py.

Framework menyediakan:
- Transkrip mentah (raw_text, immutable)
- model_probability per kata (dari faster-whisper)
- Alignment per kata (match/substitution/deletion/insertion)
- durasi audio aktual
- flag review

Framework TIDAK menyediakan:
- Penilaian benar/salah per kata (tanggung jawab BacaLaras)
- WCPM, Accuracy (tanggung jawab BacaLaras)

Konfigurasi lewat env:
- WHISPER_MODEL: base (default), tiny, small, medium, large
- WHISPER_DEVICE: cpu (default), cuda
- WHISPER_COMPUTE_TYPE: int8 (default), float16, float32
- WHISPER_CPU_THREADS: 4 (default)
- DEMO_FALLBACK: false (default), true untuk mode demo tanpa model
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from services.audio_input import resolve_duration_seconds

from reading_framework import FrameworkConfig, transcribe_reading
from reading_framework.alignment import normalize_tokens
from reading_framework.asr_engine import (
    ASRResult,
    SegmentStamp,
    WordStamp,
    load_model,
)
from reading_framework.config import SCHEMA_VERSION as _FRAMEWORK_SCHEMA_VERSION
from reading_framework.pipeline import align_transcript
from reading_framework.repository import (
    Question,
    QuestionNotFoundError,
    QuestionRepository,
)

#: Versi kontrak JSON framework yang didukung BacaLaras (integrasi #2, Fase B).
#: Sumber: reading_framework.config.SCHEMA_VERSION. Bila framework di-update dan
#: menaikkan versi ini, adapter HARUS ditinjau — penjaga di bawah akan GAGAL CEPAT
#: (bukan KeyError/None diam-diam).
EXPECTED_SCHEMA_VERSION = _FRAMEWORK_SCHEMA_VERSION


def _check_framework_contract(result: dict) -> None:
    """Penjaga kontrak framework ↔ backend (integrasi #2, Fase B).

    Memastikan ``schema_version`` cocok dan bentuk wajib ada SEBELUM ekstraksi,
    sehingga update framework yang memutus kompatibilitas gagal cepat dengan
    pesan jelas (bukan ``KeyError`` atau nilai ``None`` diam-diam).

    Raises:
        RuntimeError: bila versi berbeda atau bentuk wajib tidak lengkap.
    """
    if not isinstance(result, dict):
        raise RuntimeError(
            f"Kontrak framework tidak valid: hasil bukan dict (dapat {type(result).__name__})"
        )

    version = result.get("schema_version")
    if version is None:
        raise RuntimeError(
            "Kontrak framework tidak valid: 'schema_version' tidak ada. "
            f"Backend mengharapkan {EXPECTED_SCHEMA_VERSION!r}. Sinkronkan adapter."
        )
    if version != EXPECTED_SCHEMA_VERSION:
        raise RuntimeError(
            f"Versi kontrak framework tidak cocok: framework={version!r}, "
            f"backend mengharapkan {EXPECTED_SCHEMA_VERSION!r}. "
            "Tinjau adapter di services/speech.py sebelum melanjutkan."
        )

    # Bentuk wajib (fail-fast dengan pesan yang dapat dipahami).
    required = (
        ("transcript", "raw_text"),
        ("alignment", "words"),
        ("audio", "duration_seconds"),
    )
    for group, key in required:
        node = result.get(group)
        if not isinstance(node, dict) or key not in node:
            raise RuntimeError(
                f"Kontrak framework tidak lengkap: '{group}.{key}' tidak ada "
                f"(schema_version={version!r}). Sinkronkan adapter."
            )


# Konfigurasi dari env (dibaca saat runtime via fungsi di bawah)
def _whisper_model_name() -> str:
    return os.getenv("WHISPER_MODEL", "base")


def _whisper_device() -> str:
    return os.getenv("WHISPER_DEVICE", "cpu")


def _whisper_compute_type() -> str:
    return os.getenv("WHISPER_COMPUTE_TYPE", "int8")


def _whisper_cpu_threads() -> int:
    return int(os.getenv("WHISPER_CPU_THREADS", "4"))


def _demo_fallback_enabled() -> bool:
    return os.getenv("DEMO_FALLBACK", "false").lower() == "true"


def _count_segment_words(framework_result: dict) -> int:
    """Jumlah kata level-word dari segments[] framework (sumber flat_words)."""
    segments = (framework_result.get("transcript") or {}).get("segments") or []
    total = 0
    for seg in segments:
        total += len(seg.get("words") or [])
    return total


def apply_alignment_shift_guard(
    alignment_words: list[dict],
    framework_result: dict,
) -> list[dict]:
    """Penjaga (Fase 1B): deteksi risiko pergeseran ``model_probability``.

    Framework memasangkan probability ke kata transkrip SECARA BERURUTAN, memakai
    ``flat_words`` dari ``segments[].words``. Bila satu kata ASR pecah menjadi dua
    token setelah normalisasi (mis. tanda hubung "ke-pasar" → "ke" "pasar"),
    jumlah kata segmen ≠ jumlah token transkrip dan probability bergeser ke kata
    yang salah.

    Framework TIDAK diubah. Penjaga ini menandai kata yang berisiko sebagai
    "perlu diperiksa" (``alignment_ambiguous``) agar guru tidak menaruh percaya
    buta pada skor kata tersebut. Mengembalikan SALINAN list (framework_result
    tetap utuh sebagai audit).

    Lihat ``INTEGRATION_NOTES.md`` §6.
    """
    raw_text = (framework_result.get("transcript") or {}).get("raw_text") or ""
    n_transcript_tokens = len(normalize_tokens(raw_text))
    n_segment_words = _count_segment_words(framework_result)

    shifted = n_segment_words != n_transcript_tokens
    if not shifted:
        return alignment_words

    print(
        f"[speech] GUARD: potensi pergeseran probability "
        f"(kata segmen={n_segment_words} ≠ token transkrip={n_transcript_tokens}); "
        f"kata berisiko ditandai alignment_ambiguous."
    )

    guarded: list[dict] = []
    for item in alignment_words:
        item = dict(item)
        # Hanya kata yang benar-benar memakai probability (dicoba dibaca) yang berisiko.
        if item.get("model_probability") is not None or item.get("operation") == "substitution":
            reasons = list(item.get("review_reasons") or [])
            if "alignment_ambiguous" not in reasons:
                reasons.append("alignment_ambiguous")
            item["review_reasons"] = reasons
            item["review_required"] = True
        guarded.append(item)
    return guarded


# Model global (dimuat sekali saat startup)
_whisper_model = None
_model_info = None


@dataclass
class TranscriptResult:
    """Hasil transkrip dari framework (diteruskan ke scoring.py)."""
    raw_text: str
    alignment_words: list[dict]  # alignment.words[] dari framework
    duration_seconds: Optional[float]  # None = tak tersedia (null ≠ 0)
    framework_result: dict  # hasil lengkap untuk audit
    is_demo: bool = False


class BacaLarasQuestionRepository(QuestionRepository):
    """Adapter QuestionRepository untuk ReadingText BacaLaras.

    Framework memanggil ``repository.get(question_id)`` (lihat
    ``reading_framework.pipeline.transcribe_reading``). Implementasi WAJIB
    menyediakan ``get`` — bukan ``get_question`` — agar target text benar-benar
    ditemukan; bila tidak, framework menerima ``None`` dan ASR gagal.
    """

    def __init__(self, reading_texts: dict[str, dict]):
        """reading_texts: dict[reading_id, ReadingText dict]"""
        self.reading_texts = reading_texts

    def get(self, question_id: str) -> Question:
        """Ambil teks bacaan sebagai Question framework (kontrak framework)."""
        reading = self.reading_texts.get(question_id)
        if not reading:
            raise QuestionNotFoundError(f"reading not found: {question_id!r}")

        return Question(
            question_id=question_id,
            target_text=reading["content"],
            source_type="bacalaras_reading",
            version=reading.get("version", "v1"),
            active=True,
        )

    def exists(self, question_id: str) -> bool:
        return question_id in self.reading_texts


def load_whisper_model():
    """Muat model Whisper sekali saat startup (dipanggil dari lifespan FastAPI)."""
    global _whisper_model, _model_info
    
    if _demo_fallback_enabled():
        print(f"[speech] DEMO_FALLBACK=true, model tidak dimuat")
        return
    
    model_name = _whisper_model_name()
    device = _whisper_device()
    compute_type = _whisper_compute_type()
    cpu_threads = _whisper_cpu_threads()
    
    print(f"[speech] Loading Whisper model={model_name} device={device} compute_type={compute_type}")
    try:
        _whisper_model, _model_info = load_model(
            model_name,
            device,
            compute_type,
            cpu_threads=cpu_threads,
        )
        print(f"[speech] Model loaded: {_model_info}")
    except Exception as e:
        print(f"[speech] Failed to load model: {e}")
        if not _demo_fallback_enabled():
            raise


def transcribe(
    audio_path: str,
    reference_text: Optional[str] = None,
    reading_id: Optional[str] = None,
    reading_repository: Optional[dict[str, dict]] = None,
    output_dir: Optional[str] = None,
) -> TranscriptResult:
    """Transkripsi audio dengan framework.
    
    Args:
        audio_path: path ke file audio
        reference_text: teks acuan eksplisit (untuk test)
        reading_id: ID ReadingText (mode produksi)
        reading_repository: dict[reading_id, ReadingText dict]
        output_dir: direktori output (TXT + JSON)
    
    Returns:
        TranscriptResult dengan alignment_words[] dan durasi aktual
    
    Raises:
        RuntimeError: bila ASR gagal dan bukan mode demo
    """
    # Mode demo: putar ulang hasil framework tersimpan
    if _demo_fallback_enabled():
        target_text = reference_text
        if not target_text and reading_id and reading_repository:
            target_text = (reading_repository.get(reading_id) or {}).get("content")
        return _demo_fallback(target_text)
    
    # Persiapan repository
    repo = None
    if reading_id and reading_repository:
        repo = BacaLarasQuestionRepository(reading_repository)
    
    # Konfigurasi framework
    config = FrameworkConfig(
        model=_whisper_model_name(),
        device=_whisper_device(),
        compute_type=_whisper_compute_type(),
        cpu_threads=_whisper_cpu_threads(),
        asr_profile="raw_reading",
    )
    
    # Panggil framework
    try:
        if reference_text:
            # Mode test dengan teks eksplisit
            result = transcribe_reading(
                audio_path,
                reference_text=reference_text,
                model=_whisper_model,
                config=config,
                output_dir=output_dir,
                persist=(output_dir is not None),
            )
        elif reading_id and repo:
            # Mode produksi dengan question_id
            result = transcribe_reading(
                audio_path,
                question_id=reading_id,
                repository=repo,
                model=_whisper_model,
                config=config,
                output_dir=output_dir,
                persist=(output_dir is not None),
            )
        else:
            raise ValueError("Either reference_text or (reading_id + reading_repository) required")
        
        # Periksa status
        job_status = result.result.get("job", {}).get("status")
        alignment_status = result.result.get("alignment", {}).get("status")
        errors = result.result.get("errors", [])
        
        if job_status != "completed":
            raise RuntimeError(f"ASR job failed: status={job_status}, errors={errors}")
        
        if alignment_status != "computed":
            reason = result.result.get("alignment", {}).get("reason", "unknown")
            raise RuntimeError(f"Alignment failed: status={alignment_status}, reason={reason}")
        
        # Fase B (integrasi #2): penjaga kontrak — cek schema_version + bentuk wajib
        # SEBELUM ekstraksi, agar update framework yang memutus kompatibilitas
        # gagal cepat (bukan KeyError/None diam-diam).
        _check_framework_contract(result.result)

        # Ekstrak data
        raw_text = result.result["transcript"]["raw_text"] or ""
        alignment_words = result.result["alignment"]["words"] or []
        # Durasi: pakai nilai framework bila ada; jika tidak (mis. webm tanpa
        # ffprobe), lengkapi via PyAV di lapisan backend (null ≠ 0).
        framework_duration = result.result["audio"].get("duration_seconds")
        duration = resolve_duration_seconds(audio_path, framework_duration)

        # Penjaga pergeseran probability (Fase 1B) — tandai kata berisiko.
        alignment_words = apply_alignment_shift_guard(alignment_words, result.result)
        
        # Log performance (NFR-01: < 30 detik)
        perf = result.result.get("performance", {})
        elapsed = perf.get("elapsed_seconds", 0)
        rtf = perf.get("real_time_factor", 0)
        print(f"[speech] Processed in {elapsed:.2f}s (RTF={rtf:.2f})")
        
        return TranscriptResult(
            raw_text=raw_text,
            alignment_words=alignment_words,
            duration_seconds=duration,
            framework_result=result.result,
            is_demo=False,
        )
    
    except Exception as e:
        print(f"[speech] Transcription error: {e}")
        raise RuntimeError(f"Speech processing failed: {str(e)}")


def _demo_fallback(target_text: Optional[str] = None) -> TranscriptResult:
    """Mode demo: hasilkan transkrip+alignment deterministik TANPA model ASR.

    Dipakai saat DEMO_FALLBACK=true (mis. di lingkungan tanpa model Whisper).
    Tetap memakai aligner asli framework (`align_transcript`) agar bentuk hasil
    identik dengan jalur produksi. Setiap kata ke-7 dibuat "salah" secara
    deterministik sehingga guru melihat contoh kata benar/salah dan review flags.

    Hasil selalu ditandai ``is_demo=True`` → UI menampilkan label "Mode demo".
    """
    if not target_text or not target_text.strip():
        # Referensi tidak tersedia → contoh minimal tetap (jangan crash).
        print("[speech] DEMO mode: tanpa teks acuan, memakai contoh minimal")
        return TranscriptResult(
            raw_text="ibu pergi ke pasar",
            alignment_words=[
                {"position": 0, "reference_word": "ibu", "transcript_word": "ibu",
                 "operation": "match", "model_probability": 0.95, "start_seconds": 0.0,
                 "end_seconds": 0.5, "review_required": False, "review_reasons": []},
                {"position": 1, "reference_word": "pergi", "transcript_word": "pergi",
                 "operation": "match", "model_probability": 0.92, "start_seconds": 0.5,
                 "end_seconds": 1.0, "review_required": False, "review_reasons": []},
                {"position": 2, "reference_word": "ke", "transcript_word": "ke",
                 "operation": "match", "model_probability": 0.88, "start_seconds": 1.0,
                 "end_seconds": 1.3, "review_required": False, "review_reasons": []},
                {"position": 3, "reference_word": "pasar", "transcript_word": "pasar",
                 "operation": "match", "model_probability": 0.34, "start_seconds": 1.3,
                 "end_seconds": 2.0, "review_required": True,
                 "review_reasons": ["low_model_probability"]},
            ],
            duration_seconds=2.0,
            framework_result={"schema_version": "1.0.0", "job": {"status": "completed"}},
            is_demo=True,
        )

    # Bangun transkrip sintetis deterministik dari teks acuan.
    reference_words = target_text.split()
    spoken_words: list[str] = []
    stamps: list[WordStamp] = []
    # Asumsi laju baca ~55 kata/menit agar WCPM demo wajar (bukan angka tetap).
    duration = max(2.0, len(reference_words) / 55.0 * 60.0)
    step = duration / max(1, len(reference_words))

    for i, word in enumerate(reference_words):
        is_missed = (i % 7 == 6)  # setiap kata ke-7 dibaca keliru (deterministik)
        if is_missed:
            spoken = word[:-1] if len(word) > 2 else word + "x"
            prob = 0.3
        else:
            spoken = word
            prob = 0.9
        spoken_words.append(spoken)
        stamps.append(WordStamp(word=f" {spoken}", start=i * step, end=(i + 1) * step, probability=prob))

    asr_result = ASRResult(
        audio_path="demo",
        audio_seconds=duration,
        language_requested="id",
        language="id",
        language_probability=1.0,
        segments=[SegmentStamp(id=1, start=0.0, end=duration, text=" ".join(spoken_words), words=stamps)],
        raw_text=" ".join(spoken_words),
        applied_params={},
        model="demo",
    )

    # Pakai aligner asli framework → bentuk hasil sama dengan produksi.
    alignment = align_transcript(target_text=target_text, asr_result=asr_result)
    print("[speech] DEMO mode: transkrip sintetis deterministik (tanpa model)")

    return TranscriptResult(
        raw_text=asr_result.raw_text,
        alignment_words=alignment.get("words", []),
        duration_seconds=duration,
        framework_result={
            "schema_version": "1.0.0",
            "job": {"status": "completed"},
            "alignment": alignment,
            "audio": {"duration_seconds": duration},
        },
        is_demo=True,
    )


# ponytail: audio_duration_sec dihapus, durasi sekarang dari framework.audio.duration_seconds
