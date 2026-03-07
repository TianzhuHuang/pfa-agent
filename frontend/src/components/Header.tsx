"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createClient, hasSupabaseConfig } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

function isLocalhost(): boolean {
  if (typeof window === "undefined") return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1";
}

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!local || !domain) return email;
  const masked = local.length <= 2 ? "**" : local[0] + "***" + local[local.length - 1];
  return `${masked}@${domain}`;
}

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(() => (hasSupabaseConfig() ? undefined : null));

  // Derived (no state): avoids setState-in-effect lint and hydration mismatch.
  const showLocalMode = !hasSupabaseConfig() && isLocalhost();
  const localModeCookie = typeof document !== "undefined" && document.cookie.includes("pfa_local_mode=1");

  useEffect(() => {
    if (!hasSupabaseConfig()) return;
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    if (hasSupabaseConfig()) {
      const supabase = createClient();
      await supabase.auth.signOut();
    }
    if (typeof window !== "undefined") {
      sessionStorage.clear();
      localStorage.removeItem("pfa_chat_fallback");
    }
    router.push("/login");
    router.refresh();
  };

  const NAV_ITEMS = [
    { href: "/", label: "Portfolio" },
    { href: "/briefing", label: "Briefing" },
    // { href: "/analysis", label: "Analysis" }, // 暂时隐藏
    { href: "/settings", label: "Settings" },
  ] as const;

  if (pathname === "/login") return null;

  const isActive = (href: string) =>
    (href === "/" && (pathname === "/" || pathname?.startsWith("/portfolio"))) ||
    (href !== "/" && pathname?.startsWith(href));

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex h-12 items-center gap-2 border-b border-white/5 bg-black/95 px-6 backdrop-blur-sm">
      <Link href="/" className="flex items-center gap-2">
        <div className="relative h-8 w-8 overflow-hidden rounded-full bg-transparent">
          <Image
            src="/logo.png"
            alt="PFA"
            width={32}
            height={32}
            className="object-contain"
            priority
          />
        </div>
        <span className="text-base font-semibold text-white">PFA</span>
      </Link>
      <nav className="ml-6 flex gap-6">
        {NAV_ITEMS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`text-sm transition-colors ${isActive(href) ? "text-white" : "text-[#888888] hover:text-white"}`}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-4">
        {!hasSupabaseConfig() || localModeCookie ? (
          <>
            {(showLocalMode || localModeCookie) && <span className="text-xs text-[#888888]">本地模式</span>}
            <Link href="/logout" className="text-xs text-[#888888] hover:text-white transition-colors">
              退出
            </Link>
          </>
        ) : user === undefined ? (
          <span className="text-xs text-[#888888]">加载中...</span>
        ) : user ? (
          <>
            <span className="text-xs text-[#888888]" title={user.email ?? undefined}>
              {user.email ? maskEmail(user.email) : "已登录"}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs text-[#888888] hover:text-white transition-colors"
            >
              退出
            </button>
          </>
        ) : (
          <Link href="/login" className="text-xs text-[#888888] hover:text-white transition-colors">
            登录
          </Link>
        )}
      </div>
    </header>
  );
}
