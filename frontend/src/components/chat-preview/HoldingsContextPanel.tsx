"use client";

import React, { useMemo, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { HoldingCard, IndustryIcon, CompanyIcon, type HoldingCardItem } from "./HoldingCard";

/** 静奢风配色：行业占比图与卡片 */
const CHART_COLORS = [
  "#d4af37",
  "#748e63",
  "#c58b8b",
  "#9AA0A6",
  "#6B7280",
];

/** 涨跌与牛熊红绿：直接 hex，避免被覆盖 */
const COLOR_POSITIVE = "#748e63"; /* 绿 Bull/涨 */
const COLOR_NEGATIVE = "#c58b8b"; /* 红 Bear/跌 */

/** 标题左侧：书架/知识库图标 */
function KnowledgeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8" />
      <path d="M8 11h6" />
    </svg>
  );
}

/** 本话关联：链接图标 */
function LinkIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

interface HoldingsContextPanelProps {
  holdings: HoldingCardItem[];
  highlightedSymbols?: string[];
  industryGlowIndustries?: string[];
  /** 激活态时展示数字，如 2 表示本话关联 2 只 */
  activeSummary?: string;
}

const DEFAULT_TOP = 8;

function aggregateByIndustry(holdings: HoldingCardItem[]): { name: string; value: number }[] {
  const map = new Map<string, number>();
  for (const h of holdings) {
    const key = h.industry || "其他";
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
}

function formatPrice(price: number | null | undefined, currency?: string | null): string {
  if (price == null) return "—";
  const c = currency || "¥";
  if (price >= 1e8) return `${c}${(price / 1e8).toFixed(2)}亿`;
  if (price >= 1e4) return `${c}${price.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`;
  return `${c}${price.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
}

export function HoldingsContextPanel({
  holdings,
  highlightedSymbols = [],
  industryGlowIndustries = [],
  activeSummary,
}: HoldingsContextPanelProps) {
  const topHoldings = holdings.slice(0, DEFAULT_TOP);
  const industryData = useMemo(() => aggregateByIndustry(holdings), [holdings]);
  const activeCount = activeSummary != null ? activeSummary.replace(/\D/g, "") : "";

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(() => topHoldings[0]?.symbol ?? null);
  const selectedHolding = useMemo(
    () => topHoldings.find((h) => h.symbol === selectedSymbol) ?? topHoldings[0],
    [topHoldings, selectedSymbol]
  );

  if (topHoldings.length === 0) {
    return (
      <div className="flex h-full flex-col border-l border-white/5 bg-[#0A0F1E]/50 p-4">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#9AA0A6]">
          <KnowledgeIcon className="shrink-0 text-[#9AA0A6]" />
          持仓知识库
        </div>
        <div className="flex flex-1 items-center justify-center text-center text-sm text-[#6B7280]">
          暂无持仓，请先录入
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-l border-white/5 bg-[#0A0F1E]/50 p-4 overflow-hidden">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#9AA0A6]">
        <KnowledgeIcon className="shrink-0 text-[#D4AF37]" />
        持仓知识库
      </div>
      {activeCount && (
        <div
          className="mb-2 flex items-center gap-1.5 text-[10px] text-[var(--pfa-sentiment-neutral)]"
          title={`本话关联 ${activeCount} 只`}
        >
          <LinkIcon className="shrink-0" />
          <span>{activeCount}</span>
        </div>
      )}
      {industryData.length > 0 && (
        <div className="mb-2 shrink-0">
          <div className="text-[10px] font-medium uppercase tracking-wider text-[#6B7280] mb-1 px-0.5">
            持仓分布（按标的数）
          </div>
          <div className="h-[72px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={industryData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius="50%"
                  outerRadius="80%"
                  paddingAngle={1}
                >
                  {industryData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} stroke="none" />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TradingView 风格：自选表 - 拉长展示 */}
      <div className="min-h-0 flex-1 flex flex-col mb-2">
        <div className="text-[10px] font-medium uppercase tracking-wider text-[#6B7280] mb-1.5 px-0.5 shrink-0">
          自选
        </div>
        <div className="rounded-lg border border-white/10 bg-[#0A0F1E]/60 overflow-hidden min-h-0 flex-1">
          <div className="h-full min-h-[240px] max-h-[360px] overflow-y-auto">
            {topHoldings.map((h, i) => {
              const isSelected = h.symbol === selectedSymbol;
              const isHighlighted = highlightedSymbols.includes(h.symbol);
              const pct = h.today_pct ?? 0;
              const up = pct >= 0;
              const changeColor = up ? COLOR_POSITIVE : COLOR_NEGATIVE;
              const exchangeLabel = h.exchange || "—";
              return (
                <button
                  key={"_listKey" in h && (h as { _listKey?: string })._listKey ? (h as { _listKey: string })._listKey : `holding-${i}`}
                  type="button"
                  onClick={() => setSelectedSymbol(h.symbol)}
                  className={`flex w-full items-center gap-3 border-b border-white/5 px-3 py-2.5 text-left last:border-0 transition-colors hover:bg-white/5 ${
                    isSelected ? "bg-[#D4AF37]/10 border-l-2 border-l-[#D4AF37]" : "border-l-2 border-l-transparent"
                  } ${isHighlighted ? "ring-1 ring-[#D4AF37]/40 ring-inset" : ""}`}
                >
                  <CompanyIcon logo_url={h.logo_url} name={h.name} symbol={h.symbol} industry={h.industry} size={36} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-white">{h.name || h.symbol}</div>
                    <div className="truncate text-[11px] text-[#9AA0A6]">{h.symbol} · {exchangeLabel}</div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-medium text-white">
                      {formatPrice(h.current_price ?? null, h.currency)}
                    </div>
                    {h.today_pct != null && (
                      <div className="text-[11px] font-medium" style={{ color: changeColor }}>
                        {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 选中标的详情（TradingView 风格）- 缩短高度 */}
      {selectedHolding && (
        <div className="shrink-0 flex flex-col rounded-lg border border-white/10 bg-[#0A0F1E]/60 p-3 max-h-[180px] overflow-hidden">
          <div className="shrink-0 flex items-center gap-3 mb-2">
            <CompanyIcon logo_url={selectedHolding.logo_url} name={selectedHolding.name} symbol={selectedHolding.symbol} industry={selectedHolding.industry} size={40} />
            <div className="min-w-0">
              <div className="text-sm font-semibold text-white truncate">{selectedHolding.name || selectedHolding.symbol}</div>
              <div className="text-[11px] text-[#9AA0A6]">{selectedHolding.symbol} · {selectedHolding.exchange || (selectedHolding.industry || "—")}</div>
            </div>
          </div>
          <div className="shrink-0 mb-2">
            <div className="text-lg font-bold text-white">
              {formatPrice(selectedHolding.current_price ?? null, selectedHolding.currency)}
            </div>
            {selectedHolding.today_pct != null && (
              <span
                className="text-sm font-medium"
                style={{
                  color: selectedHolding.today_pct >= 0 ? COLOR_POSITIVE : COLOR_NEGATIVE,
                }}
              >
                {(selectedHolding.today_pct >= 0 ? "+" : "")}
                {selectedHolding.today_pct.toFixed(2)}%
              </span>
            )}
          </div>
          {(selectedHolding.market_status || selectedHolding.last_updated) && (
            <div className="text-[10px] text-[#6B7280] mb-2">
              {[selectedHolding.market_status, selectedHolding.last_updated].filter(Boolean).join(" · ")}
            </div>
          )}
          {(selectedHolding.sentiment === "positive" || selectedHolding.sentiment === "negative") && (
            <div
              className="mb-2 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
              style={{
                color: selectedHolding.sentiment === "positive" ? COLOR_POSITIVE : COLOR_NEGATIVE,
                backgroundColor: selectedHolding.sentiment === "positive" ? "rgba(116, 142, 99, 0.25)" : "rgba(197, 139, 139, 0.25)",
              }}
            >
              {selectedHolding.sentiment === "positive" ? "▲ 偏多 Bull" : "▼ 偏空 Bear"}
            </div>
          )}
          {selectedHolding.news_snippet && (
            <p className="text-[10px] text-[#9AA0A6] leading-relaxed line-clamp-2 mb-2">
              {selectedHolding.news_snippet}
            </p>
          )}
          <div className="mt-auto space-y-1 border-t border-white/5 pt-2">
            {selectedHolding.position_pct != null && selectedHolding.position_pct > 0 && (
              <div className="flex justify-between text-[10px]">
                <span className="text-[#6B7280]">仓位</span>
                <span className="text-white">{selectedHolding.position_pct.toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
