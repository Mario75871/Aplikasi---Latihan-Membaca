/**
 * app/api/proxy/[...path]/route.ts — Proxy same-origin (integrasi #5, Fase 0).
 *
 * Masalah: cookie sesi httpOnly (integrasi #4, D5) tidak dapat dibaca JS, sehingga
 * client component tidak bisa lagi mengirim `Authorization: Bearer` langsung ke
 * backend (cross-origin → cookie frontend tidak terkirim ke backend).
 *
 * Solusi: browser memanggil proxy **same-origin** ini; route handler (server) membaca
 * cookie httpOnly lalu meneruskan ke backend dengan `Bearer`. Token TIDAK pernah
 * dikembalikan ke JS. Backend hanya dilihat server (server-to-server) — CORS pun
 * lebih sempit.
 *
 *   browser → /api/proxy/students → (cookie → Bearer) → BACKEND/students
 *
 * Semua metode (GET/POST/PATCH/PUT/DELETE) lewat satu fungsi generik.
 */
import { NextResponse, type NextRequest } from "next/server";
import { cookies } from "next/headers";
import { TOKEN_COOKIE } from "@/lib/api";

/**
 * Runtime & durasi (integrasi #6, Fase D).
 *
 * - `nodejs`: fetch streaming + `duplex: "half"` andal untuk body besar.
 * - `maxDuration`: batas 300 s (maks Hobby). ASR 5 menit butuh waktu > default.
 */
export const runtime = "nodejs";
export const maxDuration = 300;

/** Base URL backend (server-side saja; jangan diekspos ke browser). */
function backendBase(): string {
  return (
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000"
  );
}

async function forward(req: NextRequest, path: string[]): Promise<NextResponse> {
  const token = (await cookies()).get(TOKEN_COOKIE)?.value ?? null;
  const target = `${backendBase()}/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  // Teruskan hanya header yang relevan. JANGAN teruskan cookie/host (cross-origin).
  const ct = req.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const accept = req.headers.get("accept");
  if (accept) headers.set("accept", accept);
  if (token) headers.set("authorization", `Bearer ${token}`);
  // Bila backend sempat diekspos lewat ngrok, header ini mencegah halaman peringatan
  // HTML "ngrok browser warning" (server-to-server). Tanpa efek di produksi (backend
  // di domain sendiri).
  headers.set("ngrok-skip-browser-warning", "true");

  const hasBody = !["GET", "HEAD"].includes(req.method);

  let res: Response;
  try {
    res = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? req.body : undefined,
      // Node fetch butuh duplex saat body berupa stream. Di runtime Edge opsinya
      // diabaikan; kita biarkan agar build TypeScript tidak menolak.
      // @ts-expect-error — duplex belum ada di tipe RequestInit standar.
      duplex: hasBody ? "half" : undefined,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return NextResponse.json(
      { detail: "Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi." },
      { status: 502 }
    );
  }

  const out = new NextResponse(res.body, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });

  // Teruskan request-id backend (untuk korelasi log lintas-sisi), bila ada.
  const backendRid = res.headers.get("X-Request-ID");
  if (backendRid) out.headers.set("X-Request-ID", backendRid);

  // 401 → sesi mati: bersihkan cookie agar klien diarahkan ke /login.
  if (res.status === 401) {
    out.cookies.set(TOKEN_COOKIE, "", { maxAge: 0, path: "/" });
  }
  return out;
}

type RouteCtx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: RouteCtx) {
  return forward(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: RouteCtx) {
  return forward(req, (await ctx.params).path);
}
export async function PUT(req: NextRequest, ctx: RouteCtx) {
  return forward(req, (await ctx.params).path);
}
export async function PATCH(req: NextRequest, ctx: RouteCtx) {
  return forward(req, (await ctx.params).path);
}
export async function DELETE(req: NextRequest, ctx: RouteCtx) {
  return forward(req, (await ctx.params).path);
}
