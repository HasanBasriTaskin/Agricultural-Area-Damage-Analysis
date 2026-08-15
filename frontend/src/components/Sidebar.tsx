"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { 
  MapPin, 
  History, 
  Users, 
  Activity, 
  LogIn, 
  LogOut, 
  ShieldAlert,
  Sprout
} from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function Sidebar() {
  const pathname = usePathname();
  const { data: session, status } = useSession();

  const userRole = session?.user?.role || "analyst";
  const isAdmin = userRole === "admin";
  const isAuthenticated = status === "authenticated" && Boolean(session?.user?.email);

  const navItems = [
    {
      label: "Harita & Analiz",
      href: "/",
      icon: MapPin,
      active: pathname === "/",
    },
    {
      label: "Analiz Geçmişi",
      href: "/jobs",
      icon: History,
      active: pathname.startsWith("/jobs"),
    },
  ];

  const adminItems = [
    {
      label: "Kullanıcı Yönetimi",
      href: "/admin/users",
      icon: Users,
      active: pathname === "/admin/users",
    },
    {
      label: "Kuyruk & İş İzleme",
      href: "/admin/jobs",
      icon: Activity,
      active: pathname === "/admin/jobs",
    },
  ];

  return (
    <aside className="w-64 bg-white/95 dark:bg-zinc-950/90 border-r border-zinc-200 dark:border-zinc-800/80 flex flex-col justify-between shrink-0 h-screen sticky top-0 backdrop-blur-xl z-50 transition-colors duration-200">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-zinc-200 dark:border-zinc-800/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 via-teal-500 to-sky-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white">
            <Sprout className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-zinc-900 dark:text-zinc-100 tracking-wide flex items-center gap-1.5">
              <span>AgriDamage</span>
              <span className="text-[10px] bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 px-1.5 py-0.5 rounded-full font-mono border border-emerald-500/30">v1.0</span>
            </h1>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">SAR + MS Hasar Füzyonu</p>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="p-3 space-y-1">
          <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 font-mono">
            Analiz & İzleme
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  item.active
                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shadow-sm font-semibold"
                    : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
                }`}
              >
                <Icon className={`w-4 h-4 ${item.active ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-500"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {/* Admin Management Section */}
          {isAdmin && (
            <>
              <div className="pt-4 pb-1">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-500/80 font-mono flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" />
                  Yönetim Paneli
                </p>
              </div>
              {adminItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                      item.active
                        ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 shadow-sm font-semibold"
                        : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900/60"
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${item.active ? "text-amber-600 dark:text-amber-400" : "text-zinc-400 dark:text-zinc-500"}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </>
          )}
        </div>
      </div>

      {/* Footer Profile & Actions */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800/80 space-y-3 bg-zinc-50/80 dark:bg-zinc-950/60 transition-colors">
        {/* User Card */}
        <div className="p-2.5 rounded-xl bg-white dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800/90 flex items-center justify-between shadow-sm">
          <div className="min-w-0 flex-1 pr-2">
            <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-200 truncate">
              {isAuthenticated ? session?.user?.email : "analyst@damage.org"}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-mono uppercase font-bold ${
                  userRole === "admin"
                    ? "bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/30"
                    : userRole === "analyst"
                    ? "bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30"
                    : "bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-400 border border-zinc-300 dark:border-zinc-700"
                }`}
              >
                {userRole}
              </span>
              <span className="text-[10px] text-zinc-500">
                {isAuthenticated ? "Aktif" : "Varsayılan"}
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons: Theme Toggle & Login/Logout */}
        <div className="flex items-center justify-between gap-2">
          <ThemeToggle />
          {isAuthenticated ? (
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-zinc-200/80 dark:bg-zinc-900 hover:bg-red-500/15 border border-zinc-300 dark:border-zinc-800 hover:border-red-500/40 text-zinc-700 dark:text-zinc-300 hover:text-red-600 dark:hover:text-red-400 text-xs font-semibold transition-all cursor-pointer shadow-sm"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Çıkış Yap</span>
            </button>
          ) : (
            <Link
              href="/login"
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-md shadow-emerald-900/20"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Giriş Yap / Değiştir</span>
            </Link>
          )}
        </div>
      </div>
    </aside>
  );
}
