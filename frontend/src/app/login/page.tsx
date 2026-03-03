"use client";

import React, { useState, useEffect, Suspense } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient, hasSupabaseConfig } from "@/lib/supabase/client";

const PHILOSOPHY = `如果乌龟能够吸取它那些最棒前辈的已经被实践所证明的洞见，有时候它也能跑赢那些追求独创性的兔子。我们赚钱，靠的是记住浅显的，而不是掌握深奥的。持续地试图别变成蠢货，久而久之，便能获得非常大的优势。`;

function isLocalhost(): boolean {
  if (typeof window === "undefined") return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1";
}

function LoginForm() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [showLocalMode, setShowLocalMode] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";

  useEffect(() => {
    setShowLocalMode(isLocalhost());
  }, []);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !password || loading) return;

    if (!hasSupabaseConfig()) {
      setMessage({ type: "error", text: "Supabase 未配置，请设置 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY" });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: trimmed,
        password,
      });

      if (error) {
        setMessage({ type: "error", text: error.message });
        setLoading(false);
        return;
      }

      router.push(redirect);
      router.refresh();
    } catch (err) {
      setMessage({
        type: "error",
        text: (err as Error).message || "登录失败，请重试",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !password || loading) return;

    if (!hasSupabaseConfig()) {
      setMessage({
        type: "error",
        text: "Supabase 未配置。请在 frontend/.env.local 中设置 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY，然后重启 dev server。",
      });
      return;
    }

    if (password.length < 6) {
      setMessage({ type: "error", text: "密码至少 6 位" });
      return;
    }

    if (password !== passwordConfirm) {
      setMessage({ type: "error", text: "两次输入的密码不一致" });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signUp({
        email: trimmed,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirect)}`,
        },
      });

      if (error) {
        setMessage({ type: "error", text: error.message });
        setLoading(false);
        return;
      }

      setMessage({
        type: "success",
        text: "注册成功！请查收邮件（含垃圾箱）中的确认链接。",
      });
    } catch (err) {
      setMessage({
        type: "error",
        text: (err as Error).message || "注册失败，请重试",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = async (provider: "google" | "github") => {
    if (!hasSupabaseConfig() || loading) return;
    setLoading(true);
    setMessage(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirect)}`,
        },
      });
      if (error) {
        setMessage({ type: "error", text: error.message });
      }
    } catch (err) {
      setMessage({ type: "error", text: (err as Error).message || "登录失败" });
    } finally {
      setLoading(false);
    }
  };

  const handleLocalMode = () => {
    if (typeof document !== "undefined") {
      document.cookie = "pfa_local_mode=1; path=/; max-age=86400";
    }
    router.push(redirect);
    router.refresh();
  };

  const inputBase =
    "flex-1 min-w-0 border-0 bg-transparent px-2 py-3 text-sm text-white placeholder:text-[#555] outline-none ring-0 focus:ring-0 disabled:opacity-50";
  const MailIcon = () => (
    <svg className="h-5 w-5 shrink-0 text-[#555]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
  const LockIcon = () => (
    <svg className="h-5 w-5 shrink-0 text-[#555]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  );
  const btnPrimary =
    "flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#22C55E] to-[#16a34a] px-4 py-3.5 text-sm font-medium text-white shadow-md shadow-[#22C55E]/20 transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-[#22C55E]/30 disabled:scale-100 disabled:opacity-70 disabled:cursor-not-allowed";

  return (
    <div className="fixed inset-0 z-40 flex flex-col items-center justify-center bg-gradient-to-b from-[#0A0A0A] to-[#121212] px-4 py-12 overflow-hidden">
      {/* 星光粒子 */}
      <div className="pointer-events-none absolute inset-0">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="absolute h-1 w-1 rounded-full bg-white"
            style={{
              left: `${10 + (i * 7) % 80}%`,
              top: `${5 + (i * 11) % 90}%`,
              animation: `pfa-particle-twinkle ${2 + (i % 3)}s ease-in-out infinite`,
              animationDelay: `${i * 0.2}s`,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 w-full max-w-[400px]">
        {/* Logo（本地环境可点击跳过登录，上线时删除） */}
        <div className="mb-8 flex justify-center">
          {showLocalMode ? (
            <button
              type="button"
              onClick={handleLocalMode}
              className="relative h-20 w-20 overflow-hidden rounded-full cursor-pointer outline-none focus:ring-2 focus:ring-[#22C55E]/50 focus:ring-offset-2 focus:ring-offset-transparent"
              style={{ animation: loading ? "pfa-logo-spin 2s linear infinite" : "pfa-breathe 3s ease-in-out infinite" }}
              title="本地模式：跳过登录"
            >
              <Image
                src="/logo.png"
                alt="PFA（点击跳过登录）"
                width={80}
                height={80}
                className="object-contain invert"
                priority
              />
            </button>
          ) : (
            <div
              className="relative h-20 w-20 overflow-hidden rounded-full"
              style={{ animation: loading ? "pfa-logo-spin 2s linear infinite" : "pfa-breathe 3s ease-in-out infinite" }}
            >
              <Image
                src="/logo.png"
                alt="PFA"
                width={80}
                height={80}
                className="object-contain invert"
                priority
              />
            </div>
          )}
        </div>

        {/* 毛玻璃卡片 */}
        <div className="rounded-2xl border border-[#222] bg-white/[0.03] p-6 backdrop-blur-md">
          {/* 登录 / 注册 切换 */}
          <div className="mb-5 flex rounded-lg bg-white/5 p-0.5">
            <button
              type="button"
              onClick={() => { setMode("login"); setMessage(null); }}
              className={`flex-1 rounded-lg px-3 py-2.5 text-sm transition ${mode === "login" ? "bg-white/15 text-white" : "text-[#888] hover:text-white"}`}
            >
              登录
            </button>
            <button
              type="button"
              onClick={() => { setMode("register"); setMessage(null); }}
              className={`flex-1 rounded-lg px-3 py-2.5 text-sm transition ${mode === "register" ? "bg-white/15 text-white" : "text-[#888] hover:text-white"}`}
            >
              注册
            </button>
          </div>

          {/* Form */}
          {mode === "login" ? (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="flex items-center gap-2 border-b border-[#333] focus-within:border-[#22C55E] transition-colors">
                <MailIcon />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                  className={inputBase}
                />
              </div>
              <div className="flex items-center gap-2 border-b border-[#333] focus-within:border-[#22C55E] transition-colors">
                <LockIcon />
                <input
                  type="password"
                  placeholder="密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                  className={inputBase}
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer text-xs text-[#888] hover:text-[#aaa]">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-[#444] bg-transparent text-[#22C55E] focus:ring-[#22C55E]"
                />
                记住我
              </label>
              <button type="submit" disabled={loading} className={btnPrimary}>
                {loading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    登录中...
                  </>
                ) : (
                  "登录"
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="flex items-center gap-2 border-b border-[#333] focus-within:border-[#22C55E] transition-colors">
                <MailIcon />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                  className={inputBase}
                />
              </div>
              <div className="flex items-center gap-2 border-b border-[#333] focus-within:border-[#22C55E] transition-colors">
                <LockIcon />
                <input
                  type="password"
                  placeholder="密码（至少 6 位）"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                  minLength={6}
                  className={inputBase}
                />
              </div>
              <div className="flex items-center gap-2 border-b border-[#333] focus-within:border-[#22C55E] transition-colors">
                <LockIcon />
                <input
                  type="password"
                  placeholder="再次输入密码"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  disabled={loading}
                  required
                  minLength={6}
                  className={inputBase}
                />
              </div>
              <button type="submit" disabled={loading} className={btnPrimary}>
                {loading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    注册中...
                  </>
                ) : (
                  "注册"
                )}
              </button>
            </form>
          )}

          <p className="mt-4 text-center text-sm text-[#888888]">
            {message?.type === "success" && (
              <span className="text-[#22C55E]">{message.text}</span>
            )}
            {message?.type === "error" && (
              <span className="text-[#ff4e33]">{message.text}</span>
            )}
          </p>

          {/* 社交登录 */}
          {hasSupabaseConfig() && (
            <div className="mt-5 flex justify-center gap-4">
              <button
                type="button"
                onClick={() => handleOAuthLogin("google")}
                disabled={loading}
                className="rounded-full p-2.5 text-[#888] transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
                title="使用 Google 登录"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
              </button>
              <button
                type="button"
                onClick={() => handleOAuthLogin("github")}
                disabled={loading}
                className="rounded-full p-2.5 text-[#888] transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
                title="使用 Github 登录"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* 品牌叙事：底部背景信仰 */}
        <div
          className="mt-16 max-w-[480px] opacity-60"
          style={{ fontFamily: "PingFang SC, Source Han Sans SC, Inter, sans-serif" }}
        >
          <p className="mb-1 text-sm font-medium text-[#6b7280]">慢慢变富</p>
          <p className="text-xs leading-relaxed text-[#6b7280]">{PHILOSOPHY}</p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="fixed inset-0 z-40 flex items-center justify-center bg-gradient-to-b from-[#0A0A0A] to-[#121212]"><span className="text-[#888888]">加载中...</span></div>}>
      <LoginForm />
    </Suspense>
  );
}
