"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon, type IconName } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import { logout as apiLogout, clearSessionToken } from "@/lib/api";

const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/dashboard", label: "Dashboard", icon: "layout-dashboard" },
  { href: "/classes", label: "Kelas", icon: "school" },
  { href: "/students", label: "Siswa", icon: "users" },
  { href: "/assess", label: "Asesmen", icon: "mic" },
  { href: "/readings", label: "Bacaan", icon: "book-open" },
];

/**
 * TeacherShell — sidebar + topbar untuk Teacher Mode.
 * Ikon memakai satu set konsisten (components/ui/icons.tsx).
 * Responsif: sidebar tetap di `lg`, berubah menjadi bar atas yang dapat digulir di mobile/tablet.
 */
export function TeacherShell({
  children,
  title,
  breadcrumb,
  actions,
  toolbar,
}: {
  children: React.ReactNode;
  title: string;
  breadcrumb?: string;
  actions?: React.ReactNode;
  /** Baris kontrol tambahan (mis. class switcher + pencarian) di bawah topbar. */
  toolbar?: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    // Token tidak lagi dibaca JS (cookie httpOnly): proxy yang menyuntik Bearer.
    await apiLogout();
    await clearSessionToken();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="flex min-h-screen bg-paper">
      {/* Sidebar — desktop */}
      <aside className="hidden w-56 shrink-0 border-r border-paper-200 bg-paper-100/50 p-4 lg:block">
        <Link href="/dashboard" className="mb-6 flex items-center gap-2.5 px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-paper">
            <Icon name="book-open" size={18} />
          </span>
          <span className="font-serif text-xl font-semibold tracking-tight text-slate-900">
            BacaLaras
          </span>
        </Link>
        <nav aria-label="Navigasi utama" className="space-y-0.5">
          {NAV.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "text-slate-900 shadow-[inset_2px_0_0_#BD582E]"
                    : "text-slate-600 hover:bg-paper-100"
                )}
              >
                <Icon
                  name={item.icon}
                  size={20}
                  className={active ? "text-brand-600" : "text-slate-400"}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-sticky border-b border-paper-200 bg-paper/95 backdrop-blur">
          <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-paper lg:hidden">
                <Icon name="book-open" size={18} />
              </span>
              <div className="min-w-0">
                {breadcrumb && (
                  <p className="truncate text-xs text-slate-400">{breadcrumb}</p>
                )}
                <h1 className="truncate font-serif text-h2 font-semibold text-slate-900">
                  {title}
                </h1>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {actions}
              <button
                type="button"
                onClick={handleLogout}
                className="hidden h-9 items-center gap-1.5 rounded-md bg-paper-100 px-3 text-sm font-medium text-slate-600 hover:bg-paper-200 focus-visible:outline-none sm:flex"
                title="Keluar"
              >
                <Icon name="log-out" size={16} />
                Keluar
              </button>
              <button
                type="button"
                onClick={handleLogout}
                aria-label="Keluar"
                className="flex h-9 w-9 items-center justify-center rounded-md bg-paper-100 text-slate-600 hover:bg-paper-200 focus-visible:outline-none sm:hidden"
              >
                <Icon name="log-out" size={18} />
              </button>
            </div>
          </div>

          {/* Nav horizontal — mobile & tablet */}
          <nav
            aria-label="Navigasi utama"
            className="flex gap-1 overflow-x-auto border-t border-paper-100 px-2 py-1 lg:hidden"
          >
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                    active
                      ? "text-slate-900 shadow-[inset_0_-2px_0_#BD582E]"
                      : "text-slate-600 hover:bg-paper-100"
                  )}
                >
                  <Icon
                    name={item.icon}
                    size={18}
                    className={active ? "text-brand-600" : "text-slate-400"}
                  />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {toolbar && (
            <div className="border-t border-paper-100 px-4 py-3 md:px-6">{toolbar}</div>
          )}
        </header>

        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
