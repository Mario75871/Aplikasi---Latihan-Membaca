import { getAudioConfig } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { MAX_AUDIO_DURATION_SEC } from "@/lib/audio-wav";
import RecordScreenLoader from "./RecordScreen";

/**
 * S-03 Rekam Suara (server component).
 *
 * Mengambil konfigurasi audio dari backend (`GET /config/audio`) di **sisi server**
 * lalu meneruskan batas durasi ke komponen klien. Ini menjadikan batas durasi
 * benar-benar **ditegakkan saat runtime** (bukan hanya test anti-drift), tanpa
 * round-trip fetch dari browser dan tanpa mengekspos token ke JS.
 *
 * Bila fetch gagal (mis. backend down), jatuh ke konstanta cermin backend
 * (`MAX_AUDIO_DURATION_SEC`) — perilaku tetap aman (backend tetap penentu akhir).
 */
export default async function StudentRecordPage() {
  const token = await getServerToken();
  const config = await getAudioConfig(token);
  const maxDurationSec = config?.maxAudioDurationSec ?? MAX_AUDIO_DURATION_SEC;

  return <RecordScreenLoader maxDurationSec={maxDurationSec} />;
}
