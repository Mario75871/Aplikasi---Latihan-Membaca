/**
 * middleware.ts — proteksi halaman guru (F-03, D7).
 *
 * Memeriksa keberadaan cookie token sesi. Bila tidak ada, pengguna diarahkan
 * ke /login. Validasi token sebenarnya tetap dilakukan backend (401 → ditangani
 * di server component / halaman error).
 */
import { NextResponse, type NextRequest } from "next/server";

const TOKEN_COOKIE = "bacalaras_token";

/** Rute guru yang wajib login. */
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/classes",
  "/students",
  "/assessments",
  "/readings",
  "/assess",
];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = req.cookies.get(TOKEN_COOKIE)?.value;

  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );

  // Sudah login → jangan tampilkan halaman login/daftar lagi.
  if ((pathname === "/login" || pathname === "/register") && token) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  if (isProtected && !token) {
    const url = new URL("/login", req.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/classes/:path*",
    "/students/:path*",
    "/assessments/:path*",
    "/readings/:path*",
    "/assess/:path*",
    "/login",
    "/register",
  ],
};
