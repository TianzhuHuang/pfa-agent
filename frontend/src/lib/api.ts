/**
 * API 请求封装 — 自动携带 Supabase JWT
 *
 * 当 Supabase 已配置且用户已登录时，在请求头注入 Authorization: Bearer <access_token>。
 *
 * API_BASE：设为 NEXT_PUBLIC_API_URL 可直连后端，绕过 Next.js 代理 30s 超时（晨报生成等长耗时场景）。
 * 本地开发：NEXT_PUBLIC_API_URL=http://localhost:8000
 * 生产：NEXT_PUBLIC_API_URL=https://api.yourdomain.com
 */

import { hasSupabaseConfig } from "./supabase/client";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const headers = new Headers(init?.headers);

  if (hasSupabaseConfig()) {
    try {
      const { createClient } = await import("./supabase/client");
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        headers.set("Authorization", `Bearer ${session.access_token}`);
      }
    } catch {
      // Supabase 未就绪或未登录，不添加 header
    }
  }

  return fetch(input, { ...init, headers });
}
