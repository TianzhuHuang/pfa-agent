/**
 * 获取站点绝对 URL，用于 auth 回调等场景。
 * 生产环境优先使用 NEXT_PUBLIC_SITE_URL，避免重定向到 0.0.0.0。
 */
export function getURL(): string {
  if (typeof window !== "undefined") {
    const env = process.env.NEXT_PUBLIC_SITE_URL?.trim();
    if (env) return env;
    if (
      window.location.origin.startsWith("http://localhost") ||
      window.location.origin.startsWith("http://127.0.0.1")
    ) {
      return window.location.origin;
    }
  }
  return process.env.NEXT_PUBLIC_SITE_URL || "https://pfa.shareyourhealth.cn";
}
