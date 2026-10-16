/**
 * app/api/session/route.ts — Pengelolaan cookie sesi httpOnly (integrasi #4, D5).
 *
 * Token disimpan di cookie **httpOnly** yang hanya bisa di-set server, sehingga JS di
 * browser tidak dapat membacanya (menutup celah XSS). Atribut `Secure` **kondisional**
 * dari env `SESSION_COOKIE_SECURE` (default false) — karena HTTPS belum tentu tersedia.
 * Jangan paksa Secure=true saat masih HTTP (cookie akan diabaikan browser).
 *
 *   POST   /api/session  → set cookie dari { token }
 *   DELETE /api/session  → hapus cookie
 */
import { NextResponse, type NextRequest } from "next/server";
import { TOKEN_COOKIE } from "@/lib/api";

const SECURE = process.env.SESSION_COOKIE_SECURE === "true";
const TTL_SEC = Number(process.env.SESSION_TTL_HOURS ?? "12") * 3600;

export async function POST(req: NextRequest) {
  let token = "";
  try {
    const body = (await req.json()) as { token?: string };
    token = body?.token ?? "";
  } catch {
    token = "";
  }
  if (!token) {
    return NextResponse.json({ detail: "Token kosong." }, { status: 422 });
  }

  const res = NextResponse.json({ status: "ok" });
  res.cookies.set(TOKEN_COOKIE, token, {
    httpOnly: true,
    secure: SECURE,
    sameSite: "lax",
    path: "/",
    maxAge: TTL_SEC,
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ status: "ok" });
  res.cookies.set(TOKEN_COOKIE, "", {
    httpOnly: true,
    secure: SECURE,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return res;
}
