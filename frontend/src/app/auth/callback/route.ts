import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const BASE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  process.env.SITE_URL ||
  "https://pfa.shareyourhealth.cn";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const token_hash = requestUrl.searchParams.get("token_hash");
  const type = requestUrl.searchParams.get("type");
  let redirect = "/";
  try {
    const raw = requestUrl.searchParams.get("redirect") || "/";
    redirect = raw.startsWith("/") ? raw : `/${raw}`;
  } catch {
    redirect = "/";
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return NextResponse.redirect(new URL("/login?error=config", BASE_URL));
  }

  const redirectUrl = new URL(redirect, BASE_URL);
  const response = NextResponse.redirect(redirectUrl);

  const cookieStore = await cookies();
  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          cookieStore.set(name, value, options);
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  try {
    if (code) {
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (error) throw error;
      return response;
    }
    if (token_hash && type) {
      // token_hash 仅用于 email OTP，type 需为 EmailOtpType
      const emailTypes = ["signup", "recovery", "invite", "email"] as const;
      const otpType = emailTypes.includes(type as (typeof emailTypes)[number])
        ? (type as (typeof emailTypes)[number])
        : "email";
      const { error } = await supabase.auth.verifyOtp({ token_hash, type: otpType });
      if (error) throw error;
      return response;
    }
  } catch (error) {
    console.error("Auth Callback Error:", error);
    return NextResponse.redirect(new URL("/login?error=auth", BASE_URL));
  }

  // Supabase 可能将 token 放在 URL hash 中（implicit flow），服务端收不到，需客户端 setSession
  const baseUrl = BASE_URL.replace(/"/g, '\\"');
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>登录中...</title></head>
<body><p>正在完成登录...</p>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script>
  (function(){
    var base = "${baseUrl}";
    var h = window.location.hash.slice(1);
    if (!h) { window.location.href = base + '/login?error=no_token'; return; }
    var p = new URLSearchParams(h);
    var at = p.get('access_token'), rt = p.get('refresh_token');
    if (!at) { window.location.href = base + '/login?error=no_token'; return; }
    var r = new URLSearchParams(window.location.search).get('redirect') || '/';
    var supabase = window.supabase.createClient("${supabaseUrl.replace(/"/g, '\\"')}", "${(supabaseAnonKey || "").replace(/"/g, '\\"')}");
    supabase.auth.setSession({ access_token: at, refresh_token: rt || '' })
      .then(function(){ window.location.href = r.startsWith('http') ? r : base + r; })
      .catch(function(){ window.location.href = base + '/login?error=session'; });
  })();
</script></body></html>`;
  return new NextResponse(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
