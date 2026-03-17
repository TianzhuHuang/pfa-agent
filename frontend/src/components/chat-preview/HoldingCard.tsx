"use client";

import React from "react";

export interface HoldingCardItem {
  symbol: string;
  name: string;
  industry: string;
  /** 可选：公司 logo 图片 URL，用于自选列表展示 */
  logo_url?: string | null;
  /** 可选：交易所/市场标签，如 NASDAQ、港交所、沪市 */
  exchange?: string | null;
  /** 可选：仓位占比 0–100，用于显示占比条 */
  position_pct?: number;
  /** 可选：最新价（TradingView 风格自选表） */
  current_price?: number | null;
  /** 可选：当日涨跌幅，如 0.5 表示 +0.5%（TradingView 风格） */
  today_pct?: number | null;
  /** 可选：价格变动绝对值（若缺则可由 current_price 与成本推算） */
  change?: number | null;
  /** 可选：货币/单位，如 ¥、HK$、$ */
  currency?: string;
  /** 可选：一句相关新闻/风险（选中详情用） */
  news_snippet?: string | null;
  /** 可选：市场状态，如 休市 / 交易中 */
  market_status?: string | null;
  /** 可选：最后更新时间 */
  last_updated?: string | null;
  /** 可选：新闻/情绪倾向，用于右侧详情红绿展示 */
  sentiment?: "positive" | "negative" | "neutral" | null;
}

interface HoldingCardProps {
  holding: HoldingCardItem;
  highlighted?: boolean;
  industryGlow?: boolean;
}

/** 行业 → 图标（SVG），供 HoldingCard 与 Watchlist 共用 */
export function IndustryIcon({ industry, className }: { industry: string; className?: string }) {
  const c = className ?? "h-5 w-5 shrink-0 text-[#9AA0A6]";
  const stroke = "currentColor";
  const strokeWidth = 1.5;
  const props = { className: c, width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke, strokeWidth, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

  if (/白酒|饮料|消费/.test(industry)) {
    return (
      <svg {...props} aria-hidden>
        <path d="M8 2h8v4l-2 12H10L8 6V2z" />
        <path d="M8 6h8" />
      </svg>
    );
  }
  if (/社交|游戏|互联/.test(industry)) {
    return (
      <svg {...props} aria-hidden>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
      </svg>
    );
  }
  if (/AI|芯片|科技|基建/.test(industry)) {
    return (
      <svg {...props} aria-hidden>
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M9 9h6M9 13h4M9 17h2" />
      </svg>
    );
  }
  if (/数字|黄金|加密|BTC/.test(industry)) {
    return (
      <svg {...props} aria-hidden>
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        <circle cx="12" cy="12" r="4" />
      </svg>
    );
  }
  return (
    <svg {...props} aria-hidden>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8M8 11h6" />
    </svg>
  );
}

/** 公司 Icon：有 logo_url 显示图片，否则显示名称首字圆标 + 行业图标兜底 */
export function CompanyIcon({
  logo_url,
  name,
  symbol,
  industry,
  size = 36,
  className,
}: {
  logo_url?: string | null;
  name: string;
  symbol: string;
  industry: string;
  size?: number;
  className?: string;
}) {
  const initial = (name || symbol || "?")[0].toUpperCase();
  const hue = (symbol.charCodeAt(0) * 7 + (symbol.length || 0)) % 360;

  if (logo_url && logo_url.startsWith("http")) {
    return (
      <img
        src={logo_url}
        alt=""
        width={size}
        height={size}
        className={`shrink-0 rounded-full object-cover bg-white/10 ${className ?? ""}`}
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div
      className={`shrink-0 flex items-center justify-center rounded-full text-white font-semibold ${className ?? ""}`}
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.44),
        backgroundColor: `hsl(${hue}, 45%, 35%)`,
      }}
      aria-hidden
    >
      {initial}
    </div>
  );
}

export function HoldingCard({ holding, highlighted, industryGlow }: HoldingCardProps) {
  const pct = holding.position_pct != null && holding.position_pct > 0 ? Math.min(100, holding.position_pct) : 0;

  return (
    <div
      className={`rounded-lg border p-3 transition-all ${
        highlighted
          ? "border-[#D4AF37]/60 bg-[#D4AF37]/10 shadow-[0_0_12px_rgba(212,175,55,0.2)]"
          : industryGlow
            ? "border-white/15 bg-white/[0.03] shadow-[0_0_8px_rgba(212,175,55,0.1)]"
            : "border-white/10 bg-[#0A0F1E]/40"
      }`}
    >
      <div className="flex items-start gap-2">
        <IndustryIcon industry={holding.industry} className="mt-0.5 h-5 w-5 shrink-0 text-[#9AA0A6]" />
        <div className="min-w-0 flex-1">
          <div className="font-medium text-white">{holding.name}</div>
          <div className="mt-0.5 text-xs text-[#9AA0A6]" title={holding.industry}>
            {holding.industry}
          </div>
          {pct > 0 && (
            <div className="mt-1.5 h-[2px] w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-[var(--pfa-sentiment-neutral)]"
                style={{ width: `${pct}%` }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
