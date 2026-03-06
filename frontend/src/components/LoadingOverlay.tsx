"use client";

/**
 * PFA 品牌化 Loading 界面
 * 使用品牌 Logo，稳扎稳打搬运数据
 */
export function LoadingOverlay({
  fullScreen = true,
  compact = false,
  text = "稳扎稳打，数据正在搬运中...",
}: {
  fullScreen?: boolean;
  compact?: boolean;
  text?: string;
}) {
  const size = compact ? 48 : 120;
  const containerClass = fullScreen
    ? "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    : "flex min-h-[200px] flex-col items-center justify-center gap-4 py-8";

  return (
    <div className={containerClass}>
      <div className="flex flex-col items-center">
        {/* 品牌 Logo，呼吸灯动画 */}
        <div
          className="pfa-loading-logo shrink-0"
          style={{ width: size, height: size }}
        >
          <img
            src="/logo.png"
            alt=""
            aria-hidden
            className="h-full w-full object-contain"
          />
        </div>
        <p
          className="text-[#666666]"
          style={{ marginTop: compact ? 12 : 20, fontSize: compact ? 12 : 14 }}
        >
          {text}
        </p>
      </div>
    </div>
  );
}
