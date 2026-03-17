"use client";

import React from "react";
import Link from "next/link";

const MOCK_CHAIN = [
  { step: "输入", detail: "用户粘贴新闻/链接/截图" },
  { step: "提取", detail: "OCR / 链接正文抽取 → 形成上下文" },
  { step: "归因", detail: "宏观因子 / 行业链条 / 资金面路径" },
  { step: "落地", detail: "映射到持仓标的，给出影响方向与关注等级" },
];

export default function DeepDivePage() {
  return (
    <div className="min-h-[calc(100vh-48px)] bg-[#0A0F1E] p-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/chat-preview"
            className="flex items-center gap-2 text-sm text-[#9AA0A6] hover:text-[#D4AF37]"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            返回对话
          </Link>
        </div>
        <h1 className="mb-2 text-xl font-semibold text-white">深度分析</h1>
        <p className="mb-8 text-sm text-[#9AA0A6]">
          逻辑推演链：新闻 → 宏观因子 → 行业影响 → 具体标的
        </p>

        <div className="space-y-0">
          {MOCK_CHAIN.map((item, i) => (
            <div key={i} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#D4AF37]/40 bg-[#D4AF37]/10 text-xs font-semibold text-[#D4AF37]">
                  {i + 1}
                </div>
                {i < MOCK_CHAIN.length - 1 && (
                  <div className="my-1 w-px flex-1 bg-white/10" />
                )}
              </div>
              <div className="pb-8">
                <div className="text-xs font-semibold uppercase tracking-wider text-[#9AA0A6]">
                  {item.step}
                </div>
                <div className="mt-1 text-sm text-white">{item.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
