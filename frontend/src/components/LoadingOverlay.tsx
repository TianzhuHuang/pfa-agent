"use client";

/**
 * PFA 品牌化 Loading 界面
 * 乌龟漫步：慢工出细活，稳扎稳打搬运数据
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
        {/* 乌龟 Logo，水平滑动动画 5s 周期 */}
        <div
          className={`pfa-turtle-walk-container shrink-0 ${compact ? "pfa-turtle-walk-compact" : ""}`}
          style={{ width: size, height: size }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 48 48"
            fill="none"
            aria-hidden
            className="h-full w-full"
          >
            <path
              d="M10 26 C10 14 24 8 38 26 L38 30 L10 30 Z"
              stroke="#4285F4"
              strokeWidth="1.4"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M24 12 L30 16 L30 24 L24 28 L18 24 L18 16 Z"
              stroke="#4285F4"
              strokeWidth="1"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M14 18 L18 20 L18 26 L14 28 L10 26 L10 20 Z"
              stroke="#4285F4"
              strokeWidth="0.8"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M34 18 L38 20 L38 26 L34 28 L30 26 L30 20 Z"
              stroke="#4285F4"
              strokeWidth="0.8"
              strokeLinejoin="round"
              fill="none"
            />
            <ellipse
              cx="6"
              cy="26"
              rx="4"
              ry="3"
              stroke="#4285F4"
              strokeWidth="1.4"
              fill="none"
            />
            <circle cx="5" cy="25" r="0.8" fill="#4285F4" />
            <path
              d="M3 27 Q5 28 7 27"
              stroke="#4285F4"
              strokeWidth="0.7"
              strokeLinecap="round"
              fill="none"
            />
            <path d="M10 30 L38 30" stroke="#4285F4" strokeWidth="1.2" />
            <path
              d="M16 30 L16 35 Q16 37 18 37 L20 35"
              stroke="#4285F4"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M32 30 L32 35 Q32 37 34 37 L36 35"
              stroke="#4285F4"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
            <path
              d="M38 28 L41 29"
              stroke="#4285F4"
              strokeWidth="1"
              strokeLinecap="round"
            />
          </svg>
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
