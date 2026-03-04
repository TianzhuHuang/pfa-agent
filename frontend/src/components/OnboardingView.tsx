"use client";

import Image from "next/image";

interface OnboardingViewProps {
  onOpenEntry: (tab: "search" | "ocr" | "file") => void;
}

const FEATURES = [
  {
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
    title: "全球追踪",
    desc: "A 股、美股、港股及加密货币，自动换算汇率",
  },
  {
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: "AI 简报",
    desc: "基于你的持仓，每日生成专属的 AI 投资周报",
  },
  {
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: "收益归因",
    desc: "直观查看股息、分红及不同维度的资产占比",
  },
];

const CARDS = [
  {
    id: "search" as const,
    title: "手动添加",
    subtitle: "搜索并录入单笔交易",
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
  },
  {
    id: "file" as const,
    title: "批量导入",
    subtitle: "支持导出 CSV/Excel 文件上传",
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    ),
  },
  {
    id: "ocr" as const,
    title: "账户截图智能同步",
    subtitle: "识别券商账户截图，自动同步持仓",
    icon: (
      <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
];

export function OnboardingView({ onOpenEntry }: OnboardingViewProps) {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-4 py-16">
      <div className="mx-auto w-full max-w-2xl text-center">
        {/* Hero: Turtle logo with breathing animation */}
        <div className="mb-6 flex justify-center">
          <div
            className="relative h-20 w-20 overflow-hidden rounded-full"
            style={{ animation: "pfa-breathe 3s ease-in-out infinite" }}
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
        </div>

        {/* Feature Highlights — Ghost List（不可点击的信息展示） */}
        <div className="mb-12 flex flex-col gap-3 sm:flex-row sm:justify-center sm:gap-8">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="flex items-center gap-2 sm:gap-3 text-left"
            >
              <span className="shrink-0 text-[#9ca3af]">{f.icon}</span>
              <div>
                <span className="text-sm font-medium text-[#9ca3af]">{f.title}</span>
                <span className="text-xs text-[#6b7280]"> · {f.desc}</span>
              </div>
            </div>
          ))}
        </div>

        {/* 过渡引导语 */}
        <p
          className="mb-8 text-center text-lg font-semibold text-[#22c55e]/80"
          style={{ animation: "pfa-fade-in 0.5s ease-out forwards" }}
        >
          那么，开始录入你的第一笔持仓吧？
        </p>

        {/* Three Entry Cards — 升权，Hover 发光 */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:gap-6">
          {CARDS.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => onOpenEntry(c.id)}
              className="group flex flex-1 flex-col items-center rounded-xl border border-[#222] bg-[#0a0a0a] px-6 py-6 transition-all duration-200 hover:border-[#22c55e]/60 hover:bg-[#111] hover:shadow-[0_0_15px_rgba(34,197,94,0.2)]"
            >
              <span className="mb-3 text-[#22c55e] transition-colors group-hover:text-[#22c55e]/90">
                {c.icon}
              </span>
              <div className="flex items-center gap-1.5 font-semibold text-white">
                {c.title}
                <span className="text-[#22c55e] opacity-50 transition-opacity group-hover:opacity-100">→</span>
              </div>
              <div className="mt-1 text-xs text-[#888888]">{c.subtitle}</div>
            </button>
          ))}
        </div>

        {/* Hint */}
        <p className="text-xs text-[#666]">
          录入后，PFA 将自动激活您的 AI 简报和资产分布看板。
        </p>
      </div>
    </div>
  );
}
