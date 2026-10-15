import { LandingPage } from "@/components/landing/LandingPage";
import { getServerToken } from "@/lib/api-server";

/**
 * Rute `/` — Landing page publik (F-00).
 *
 * - TANPA autentikasi dan TANPA panggilan API backend/database (halaman statis).
 * - Bila guru sudah login, landing TETAP tampil, tetapi CTA berubah menjadi
 *   "Ke Dashboard" (D8 / Q12). Pengecekan hanya membaca keberadaan cookie sesi
 *   di server, bukan memanggil backend.
 */
export default async function Home() {
  const token = await getServerToken();
  return <LandingPage isLoggedIn={Boolean(token)} />;
}
