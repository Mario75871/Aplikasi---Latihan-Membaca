/**
 * Konversi audio hasil MediaRecorder (biasanya webm/opus) → WAV (PCM 16-bit mono 16 kHz).
 *
 * Latar (integrasi #3, D4): backend hanya menerima **WAV & MP3** dan menolak webm
 * dengan 415. Browser merekam webm via MediaRecorder, jadi kita decode ke PCM
 * memakai Web Audio API lalu bungkus sebagai WAV. Tidak menambah dependency.
 *
 * Integrasi #4 (D2): standar input ASR = **16 kHz mono**. Rekaman 48 kHz mono 2 menit
 * ≈ 11 MB (melebihi batas 10 MB) → kita **resample** ke 16 kHz (≈ 3.8 MB) memakai
 * resampler bawaan browser (`OfflineAudioContext`), bukan decimasi kasar (anti-alias).
 */

/**
 * Sample rate standar input ASR (integrasi #4, D2). Satu tempat untuk seluruh klien.
 * Harus mencerminkan `TARGET_SAMPLE_RATE` backend.
 */
export const TARGET_SAMPLE_RATE = 16000;

/** Batas ukuran upload (byte) — mencerminkan `MAX_AUDIO_BYTES` backend (D3/D4). */
export const MAX_AUDIO_BYTES = 10 * 1024 * 1024; // 10 MB

/**
 * Batas **durasi** upload (detik) — cermin `MAX_AUDIO_DURATION_SEC` backend
 * (default 300 = 5 menit). Integrasi #6 (D1c): dipakai HANYA sebagai **fallback**
 * bila `GET /config/audio` gagal; sumber runtime utama tetap backend.
 */
export const MAX_AUDIO_DURATION_SEC = 300;

/** Bungkus PCM Float32 mono 16-bit menjadi container WAV. */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true); // PCM chunk size
  view.setUint16(20, 1, true); // format = PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}

/** WAV senyap minimal (valid) — untuk jalur demo "Pakai Audio Contoh". */
export function makeSilentWavBlob(sampleRate = 8000, nSamples = 8): Blob {
  return encodeWav(new Float32Array(nSamples), sampleRate);
}

/**
 * Resample + downmix ke mono 16 kHz memakai `OfflineAudioContext` (integrasi #4, D2).
 *
 * Memakai resampler bawaan browser (kualitas baik, anti-alias) alih-alih decimasi
 * kasar. Kembalikan PCM mono pada `TARGET_SAMPLE_RATE`.
 */
async function resampleTo16k(audio: AudioBuffer): Promise<Float32Array> {
  const target = TARGET_SAMPLE_RATE;
  // Sudah sesuai target → cukup downmix.
  if (audio.sampleRate === target && audio.numberOfChannels === 1) {
    return audio.getChannelData(0).slice();
  }

  const frames = Math.max(1, Math.ceil((audio.length * target) / audio.sampleRate));
  const OfflineCtx: typeof OfflineAudioContext =
    window.OfflineAudioContext ||
    (window as unknown as { webkitOfflineAudioContext: typeof OfflineAudioContext })
      .webkitOfflineAudioContext;

  const offline = new OfflineCtx(1, frames, target);
  const src = offline.createBufferSource();
  src.buffer = audio;
  src.connect(offline.destination);
  src.start();
  const rendered = await offline.startRendering();
  return rendered.getChannelData(0);
}

/**
 * Konversi Blob audio apa pun yang dapat didekode browser → WAV 16 kHz mono.
 * Melempar error bila gagal (pemanggil menangani fallback).
 */
export async function blobToWav(input: Blob): Promise<Blob> {
  const arrayBuf = await input.arrayBuffer();
  const AudioCtx: typeof AudioContext =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioCtx();
  let audio: AudioBuffer;
  try {
    audio = await ctx.decodeAudioData(arrayBuf.slice(0));
  } finally {
    ctx.close();
  }
  const samples = await resampleTo16k(audio);
  return encodeWav(samples, TARGET_SAMPLE_RATE);
}
