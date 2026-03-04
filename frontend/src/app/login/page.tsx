"use client";

import React, { useState, Suspense } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { createClient, hasSupabaseConfig } from "@/lib/supabase/client";
import { getURL } from "@/lib/supabase/url";

const PHILOSOPHY = `如果乌龟能够吸取它那些最棒前辈的已经被实践所证明的洞见，有时候它也能跑赢那些追求独创性的兔子。我们赚钱，靠的是记住浅显的，而不是掌握深奥的。持续地试图别变成蠢货，久而久之，便能获得非常大的优势。`;

function isLocalhost(): boolean {
  if (typeof window === "undefined") return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1";
}

function enterLocalMode(router: ReturnType<typeof useRouter>, redirect: string) {
  document.cookie = "pfa_local_mode=1; path=/; max-age=86400; SameSite=Lax";
  router.push(redirect);
  router.refresh();
}

function LoginForm() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [registerSuccess, setRegisterSuccess] = useState(false);
  const [registerEmail, setRegisterEmail] = useState("");
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !password || loading) return;

    if (!hasSupabaseConfig()) {
      setMessage({ type: "error", text: "Supabase 未配置。本地：设置 frontend/.env.local；生产：确认 .env 中有 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY 后重新构建。" });
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
        text: "Supabase 未配置。本地开发：在 frontend/.env.local 设置 NEXT_PUBLIC_SUPABASE_URL 和 NEXT_PUBLIC_SUPABASE_ANON_KEY 后重启。生产环境：确认项目根目录 .env 中有上述变量后重新构建并部署。",
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
          emailRedirectTo: `${getURL()}/auth/callback?redirect=${encodeURIComponent(redirect)}`,
        },
      });

      if (error) {
        setMessage({ type: "error", text: error.message });
        setLoading(false);
        return;
      }

      setRegisterEmail(trimmed);
      setRegisterSuccess(true);
    } catch (err) {
      setMessage({
        type: "error",
        text: (err as Error).message || "注册失败，请重试",
      });
    } finally {
      setLoading(false);
    }
  };

  const inputWrapper =
    "flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 transition-colors focus-within:border-[#22C55E]/40 focus-within:bg-white/[0.07]";
  const inputBase =
    "flex-1 min-w-0 border-0 bg-transparent px-0 py-3 text-sm text-white placeholder:text-[#666] outline-none ring-0 focus:ring-0 disabled:opacity-50";
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
        {/* Logo（小乌龟）：localhost + Supabase 已配置时，点击进入本地模式） */}
        <div className="mb-8 flex justify-center">
          <button
            type="button"
            onClick={() => hasSupabaseConfig() && isLocalhost() && !loading && enterLocalMode(router, redirect)}
            className={`relative h-20 w-20 overflow-hidden rounded-full cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#22C55E]/50 ${
              hasSupabaseConfig() && isLocalhost() ? "hover:opacity-90" : "cursor-default"
            }`}
            style={{ animation: loading ? "pfa-logo-spin 2s linear infinite" : "pfa-breathe 3s ease-in-out infinite" }}
            title={hasSupabaseConfig() && isLocalhost() ? "点击进入本地模式" : undefined}
          >
            <Image
              src="/logo.png"
              alt="PFA"
              width={80}
              height={80}
              className="object-contain invert"
              priority
            />
          </button>
        </div>

        {/* 毛玻璃卡片 */}
        <div className="rounded-2xl border border-[#222] bg-white/[0.03] p-6 backdrop-blur-md">
          <AnimatePresence mode="wait">
            {registerSuccess ? (
              <motion.div
                key="register-success"
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ duration: 0.25 }}
                className="space-y-6"
              >
                <div className="flex flex-col items-center text-center">
                  <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#22C55E]/20">
                    <svg className="h-7 w-7 text-[#22C55E]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <h3 className="mb-2 text-lg font-medium text-white">确认邮件已发送</h3>
                  <p className="mb-1 text-sm leading-relaxed text-[#aaa]">
                    我们已向 <span className="font-medium text-[#22C55E]">{registerEmail}</span> 发送确认链接
                  </p>
                  <p className="text-xs text-[#888]">请查收邮件（含垃圾箱）并点击链接完成注册</p>
                </div>
                <button
                  type="button"
                  onClick={() => { setRegisterSuccess(false); setMode("login"); setMessage(null); }}
                  className={btnPrimary}
                >
                  返回登录
                </button>
              </motion.div>
            ) : (
              <>
                {/* 登录 / 注册 Tab（底线滑动） */}
                <div className="relative mb-5 flex">
                  <button
                    type="button"
                    onClick={() => { setMode("login"); setMessage(null); }}
                    className={`relative z-10 flex-1 px-3 py-2.5 text-sm font-medium transition ${mode === "login" ? "text-white" : "text-[#888] hover:text-white"}`}
                  >
                    登录
                  </button>
                  <button
                    type="button"
                    onClick={() => { setMode("register"); setMessage(null); }}
                    className={`relative z-10 flex-1 px-3 py-2.5 text-sm font-medium transition ${mode === "register" ? "text-white" : "text-[#888] hover:text-white"}`}
                  >
                    注册
                  </button>
                  <motion.div
                    className="absolute bottom-0 h-0.5 bg-[#22C55E]"
                    layoutId="login-tab-indicator"
                    initial={false}
                    animate={{ left: mode === "login" ? 0 : "50%" }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    style={{ width: "50%" }}
                  />
                </div>

                {/* Form */}
                {mode === "login" ? (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className={inputWrapper}>
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
              <div className={inputWrapper}>
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
              <div className={inputWrapper}>
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
              <div className={inputWrapper}>
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
              <div className={inputWrapper}>
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

                {/* 本地模式入口：localhost 下可跳过登录 */}
          {hasSupabaseConfig() && isLocalhost() && (
            <div className="mt-5 pt-4 border-t border-white/10">
              <button
                type="button"
                onClick={() => !loading && enterLocalMode(router, redirect)}
                disabled={loading}
                className="w-full text-center text-sm text-[#888] hover:text-[#22C55E] transition-colors disabled:opacity-50"
              >
                进入本地模式（跳过登录）
              </button>
            </div>
          )}

              </>
            )}
          </AnimatePresence>
        </div>

        {/* 品牌叙事：底部背景信仰 */}
        <div
          className="mt-16 max-w-[480px] opacity-60"
          style={{ fontFamily: "PingFang SC, Source Han Sans SC, Inter, sans-serif" }}
        >
          <p className="mb-1 text-sm font-medium leading-relaxed text-[#6b7280]">慢慢变富</p>
          <p className="text-xs leading-loose text-[#6b7280]">{PHILOSOPHY}</p>
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
