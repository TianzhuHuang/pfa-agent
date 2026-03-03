"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient, hasSupabaseConfig } from "@/lib/supabase/client";

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    const doLogout = async () => {
      if (typeof window !== "undefined") {
        sessionStorage.clear();
        localStorage.removeItem("pfa_chat_fallback");
        document.cookie = "pfa_local_mode=; path=/; max-age=0";
      }
      if (hasSupabaseConfig()) {
        const supabase = createClient();
        await supabase.auth.signOut();
      }
      router.replace("/login");
    };
    doLogout();
  }, [router]);

  return (
    <div className="flex min-h-[calc(100vh-48px)] flex-col items-center justify-center gap-4 p-6">
      <p className="text-sm text-[#888888]">已退出</p>
      <Link href="/login" className="text-sm text-[#00e701] hover:underline">
        返回登录
      </Link>
    </div>
  );
}
