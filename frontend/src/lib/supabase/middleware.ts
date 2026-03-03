import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/logout", "/auth/callback"];
const PROTECTED_PATHS = ["/", "/portfolio", "/briefing", "/analysis", "/settings"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

function isProtectedPath(pathname: string): boolean {
  if (pathname === "/") return true;
  return (
    pathname.startsWith("/portfolio") ||
    pathname.startsWith("/briefing") ||
    pathname.startsWith("/analysis") ||
    pathname.startsWith("/settings")
  );
}

export async function updateSession(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return NextResponse.next();
  }

  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        supabaseResponse = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
  });

  // 本地模式：localhost 下可通过点击 logo 进入，跳过 Supabase 认证
  const isLocalhost =
    request.nextUrl.hostname === "localhost" || request.nextUrl.hostname === "127.0.0.1";
  const localModeCookie = request.cookies.get("pfa_local_mode")?.value;
  if (isLocalhost && localModeCookie === "1" && isProtectedPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const { data } = await supabase.auth.getUser();

  if (!data?.user && isProtectedPath(request.nextUrl.pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
