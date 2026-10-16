"use client";

/**
 * AudioPlayer — pemutar rekaman siswa.
 *
 * Menerima **signed URL** berumur pendek dari server component (yang mengambil via
 * `getAssessmentAudioUrl`). Bila `url` null → tampilkan pesan "tidak tersedia"
 * (null != tombol rusak). Presentasi saja — tanpa logika penilaian.
 *
 * Catatan: signed URL kedaluwarsa bila halaman dibuka lama → muat ulang halaman
 * untuk mendapatkan URL baru (jangan simpan di state lama).
 */
export function AudioPlayer({ url }: { url: string | null }) {
  if (!url) {
    return (
      <p className="text-sm text-slate-500">
        Rekaman tidak tersedia untuk asesmen ini.
      </p>
    );
  }
  return (
    <div className="space-y-2">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio controls src={url} className="w-full">
        Peramban Anda tidak mendukung pemutar audio.
      </audio>
      <p className="text-xs text-slate-400">
        Tautan rekaman berlaku terbatas waktu. Muat ulang halaman bila sudah kedaluwarsa.
      </p>
    </div>
  );
}
