/**
 * lib/api-server.ts — Helper khusus server component.
 *
 * Mengimpor `next/headers` (server-only) untuk membaca token sesi dari cookie,
 * lalu meneruskannya ke klien API (`lib/api.ts`). Dipisah dari `lib/api.ts`
 * agar file itu tetap aman diimpor oleh client component.
 */
import { cookies } from "next/headers";
import { TOKEN_COOKIE } from "./api";

/** Baca token sesi dari cookie (server component). */
export async function getServerToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(TOKEN_COOKIE)?.value ?? null;
}
