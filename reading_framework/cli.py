"""CLI terpadu: ``python -m reading_framework <command>``.

Perintah:
    transcribe   Transkripsi satu audio (+ alignment bila referensi tersedia)
    schema       Cetak JSON Schema kontrak 1.0.0

Contoh:
    python -m reading_framework transcribe \\
        --audio audio/indo_1-1_correct.wav \\
        --reference-file audio/ref.txt \\
        --output-dir results/job-001 \\
        --profile raw_reading \\
        --format txt,json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .config import PROFILE_BASELINE, PROFILE_RAW_READING, FrameworkConfig


def _read_reference(audio: Path, explicit: str | None) -> str | None:
    if explicit:
        ref_file = Path(explicit)
        if not ref_file.is_file():
            raise FileNotFoundError(f"reference file not found: {ref_file}")
        return ref_file.read_text(encoding="utf-8").strip()
    sidecar = audio.with_suffix(".txt")
    if sidecar.is_file():
        return sidecar.read_text(encoding="utf-8").strip()
    return None


def cmd_transcribe(args) -> int:
    from .asr_engine import import_faster_whisper  # noqa: F401 - early env check
    from .pipeline import transcribe_reading
    from .repository import LocalQuestionRepository

    audio = Path(args.audio)
    if not audio.is_file():
        print(f"[!] audio file not found: {audio}", file=sys.stderr)
        return 2

    repository = None
    reference_text = None
    if args.question_id:
        if not args.question_bank:
            print("[!] --question-id requires --question-bank", file=sys.stderr)
            return 2
        repository = LocalQuestionRepository.from_file(args.question_bank)
    else:
        try:
            reference_text = _read_reference(audio, args.reference_file)
        except FileNotFoundError as exc:
            print(f"[!] {exc}", file=sys.stderr)
            return 1

    cfg = FrameworkConfig(
        asr_profile=args.profile,
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        cpu_threads=args.threads,
        num_workers=args.num_workers,
        language=("id" if args.language in (None, "auto") else args.language),
        spelling_normalization_enabled=bool(getattr(args, "spelling_normalization", False)),
    )

    formats = {f.strip().lower() for f in (args.format or "txt,json").split(",") if f.strip()}
    persist = bool(args.output_dir) and bool(formats)

    try:
        result = transcribe_reading(
            audio,
            reference_text=reference_text,
            question_id=args.question_id,
            repository=repository,
            config=cfg,
            output_dir=args.output_dir,
            persist=persist,
            overwrite=args.overwrite,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[!] pipeline failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    r = result.result
    if not result.asr_ok:
        print(f"[!] ASR failed: {r['errors']}", file=sys.stderr)

    print("=" * 78)
    print(f"JOB {r['job']['job_id']}  status={r['job']['status']}  profile={r['asr']['profile']}")
    print(f"  audio     : {r['audio']['source_filename']} "
          f"({r['audio']['duration_seconds']}s)")
    print(f"  language  : detected={r['asr']['language_detected']} "
          f"requested={r['asr']['language_requested']}")
    print(f"  performance: elapsed={r['performance']['elapsed_seconds']}s "
          f"rtf={r['performance']['real_time_factor']}")
    print("-" * 78)
    print(f"  RAW TRANSCRIPT: {r['transcript']['raw_text']}")
    al = r["alignment"]
    print(f"  alignment : {al['status']}" + (f" ({al.get('reason')})" if al.get('reason') else ""))
    if al["status"] == "computed":
        print(f"  WER={al['wer']}  CER={al['cer']}  "
              f"S/D/I={al['substitutions']}/{al['deletions']}/{al['insertions']}")
    print(f"  review    : required={r['review']['review_required']} "
          f"items={len(r['review']['items'])}")
    print("=" * 78)

    if result.raw_text_path:
        print(f"[export] TXT  -> {result.raw_text_path}")
    if result.json_path:
        print(f"[export] JSON -> {result.json_path}")
    return 0 if result.asr_ok else 1


def cmd_schema(args) -> int:
    from .schemas import json_schema
    print(json.dumps(json_schema(), indent=2, ensure_ascii=False))
    return 0


def cmd_compare_decoding(args) -> int:
    """Eksperimen: bandingkan ASR dengan vs tanpa petunjuk decoding."""
    from .asr_engine import import_faster_whisper, load_model  # noqa: F401
    from .experiments import compare_with_and_without_hint

    audio = Path(args.audio)
    if not audio.is_file():
        print(f"[!] audio file not found: {audio}", file=sys.stderr)
        return 2

    reference_text = None
    if args.reference_file:
        ref = Path(args.reference_file)
        if not ref.is_file():
            print(f"[!] reference file not found: {ref}", file=sys.stderr)
            return 1
        reference_text = ref.read_text(encoding="utf-8").strip()

    hint: dict = {}
    if args.initial_prompt:
        hint["initial_prompt"] = args.initial_prompt
    if args.hotwords:
        # faster-whisper 1.2.1 menerima hotwords sebagai STRING, bukan list.
        hint["hotwords"] = args.hotwords
    if not hint:
        print("[!] provide at least one of --initial-prompt / --hotwords",
              file=sys.stderr)
        return 2

    print("[warn] EXPERIMENT ONLY: hints must not be used in the production path",
          file=sys.stderr)

    model, _ = load_model(args.model, args.device, args.compute_type, args.threads)

    cmp = compare_with_and_without_hint(
        model, audio, reference_text=reference_text, hint=hint, language=args.language,
    )

    print("=" * 78)
    print(f"COMPARE-DECODING  audio={audio.name}  hint={hint}")
    print("-" * 78)
    print(f"  without hint raw : {cmp.without_hint_raw_text}")
    print(f"  with hint raw    : {cmp.with_hint_raw_text}")
    if reference_text is not None:
        print(f"  WER without/with : {cmp.without_hint_wer} -> {cmp.with_hint_wer} "
              f"(delta={cmp.wer_delta})")
        print(f"  CER without/with : {cmp.without_hint_cer} -> {cmp.with_hint_cer} "
              f"(delta={cmp.cer_delta})")
    print(f"  normalization    : {cmp.normalization_profile}")
    for n in cmp.notes:
        print(f"  note             : {n}")
    print("=" * 78)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m reading_framework",
        description="Raw ASR + target-based alignment untuk tes baca anak Indonesia.",
    )
    sub = parser.add_subparsers(dest="command")

    t = sub.add_parser("transcribe", help="transkripsi satu file audio")
    t.add_argument("--audio", required=True, help="path audio (wav/mp3/m4a/...)")
    t.add_argument("--reference-file", default=None,
                   help="teks acuan (dev mode); default <audio>.txt bila ada")
    t.add_argument("--question-id", default=None,
                   help="id soal; target diambil dari --question-bank")
    t.add_argument("--question-bank", default=None,
                   help="path bank soal JSON (wajib bila --question-id dipakai)")
    t.add_argument("--output-dir", default=None, help="direktori output")
    t.add_argument("--format", default="txt,json", help="txt,json (default: txt,json)")
    t.add_argument("--profile", default=PROFILE_RAW_READING,
                   choices=[PROFILE_RAW_READING, PROFILE_BASELINE])
    t.add_argument("--model", default="base")
    t.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    t.add_argument("--compute-type", default="int8")
    t.add_argument("--threads", type=int, default=4)
    t.add_argument("--num-workers", type=int, default=1)
    t.add_argument("--language", default="id")
    t.add_argument("--spelling-normalization", action="store_true",
                   help="aktifkan normalisasi ejaan ID opsional (default: nonaktif)")
    t.add_argument("--overwrite", action="store_true",
                   help="izinkan menimpa file output yang sudah ada")
    t.set_defaults(func=cmd_transcribe)

    s = sub.add_parser("schema", help="cetak JSON Schema kontrak")
    s.set_defaults(func=cmd_schema)

    c = sub.add_parser("compare-decoding",
                       help="EXPERIMENT: ASR dengan vs tanpa prompt/hotwords")
    c.add_argument("--audio", required=True)
    c.add_argument("--reference-file", default=None)
    c.add_argument("--initial-prompt", default=None)
    c.add_argument("--hotwords", default=None, help="daftar kata dipisah koma")
    c.add_argument("--model", default="base")
    c.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    c.add_argument("--compute-type", default="int8")
    c.add_argument("--threads", type=int, default=4)
    c.add_argument("--language", default="id")
    c.set_defaults(func=cmd_compare_decoding)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
