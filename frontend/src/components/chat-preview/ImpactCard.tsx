"use client";

import React, { useState } from "react";
import Link from "next/link";

export interface ImpactItem {
  symbol: string;
  name: string;
  level: "high" | "medium" | "low";
  levelLabel: string;
  sentiment?: "positive" | "negative" | "neutral";
}

interface ImpactCardProps {
  title: string;
  impacts: ImpactItem[];
  summary: string;
  onAssetClick?: (symbol: string) => void;
  deepDiveHref?: string;
}

/** 静奢红绿：直接使用 hex，避免被 Tailwind/父级覆盖 */
const SENTIMENT_POSITIVE = "#748e63"; /* 鼠尾草绿 Bull */
const SENTIMENT_NEGATIVE = "#c58b8b"; /* 尘玫瑰 Bear */
const SENTIMENT_NEUTRAL = "#d4af37";  /* 香槟金 */

function getImpactStyle(
  level: ImpactItem["level"],
  sentiment?: ImpactItem["sentiment"]
): React.CSSProperties | undefined {
  if (sentiment === "positive")
    return { color: SENTIMENT_POSITIVE, borderColor: `${SENTIMENT_POSITIVE}80`, backgroundColor: `${SENTIMENT_POSITIVE}1a` };
  if (sentiment === "negative")
    return { color: SENTIMENT_NEGATIVE, borderColor: `${SENTIMENT_NEGATIVE}80`, backgroundColor: `${SENTIMENT_NEGATIVE}1a` };
  if (level === "high")
    return { color: SENTIMENT_NEUTRAL, borderColor: `${SENTIMENT_NEUTRAL}66`, backgroundColor: `${SENTIMENT_NEUTRAL}0d` };
  if (level === "medium") return undefined; /* 使用默认 class */
  return undefined;
}

/** 根据 title 或 impacts 推断卡片类型，用于标题前图标 */
function titleCardType(title: string, impacts: ImpactItem[]): "negative" | "positive" | "neutral" {
  if (/警告|风险|利空|偏差|收紧/.test(title)) return "negative";
  if (/利好|机会|受益/.test(title)) return "positive";
  const hasNeg = impacts.some((i) => i.sentiment === "negative");
  const hasPos = impacts.some((i) => i.sentiment === "positive");
  if (hasNeg && !hasPos) return "negative";
  if (hasPos && !hasNeg) return "positive";
  return "neutral";
}

function TitleIcon({ type }: { type: "negative" | "positive" | "neutral" }) {
  const c = "h-4 w-4 shrink-0";
  const stroke = "currentColor";
  const strokeWidth = 2;
  const color = type === "negative" ? SENTIMENT_NEGATIVE : type === "positive" ? SENTIMENT_POSITIVE : SENTIMENT_NEUTRAL;
  const props = { className: c, width: 16, height: 16, viewBox: "0 0 24 24", fill: "none" as const, stroke, strokeWidth, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, style: { color } as React.CSSProperties };
  if (type === "negative") {
    return (
      <svg {...props} aria-hidden>
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <path d="M12 9v4M12 17h.01" />
      </svg>
    );
  }
  if (type === "positive") {
    return (
      <svg {...props} aria-hidden>
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <path d="M22 4L12 14.01l-3-3" />
      </svg>
    );
  }
  return (
    <svg {...props} aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  );
}

function ImpactTagIcon({ level, sentiment }: { level: ImpactItem["level"]; sentiment?: ImpactItem["sentiment"] }) {
  const c = "h-3 w-3 shrink-0";
  const stroke = "currentColor";
  const strokeWidth = 2;
  const props = { className: c, width: 12, height: 12, viewBox: "0 0 24 24", fill: "none" as const, stroke, strokeWidth, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (sentiment === "positive") {
    return <svg {...props}><path d="M12 19V5M5 12l7-7 7 7" /></svg>;
  }
  if (sentiment === "negative") {
    return <svg {...props}><path d="M12 5v14M5 12l7 7 7-7" /></svg>;
  }
  if (level === "high") {
    return (
      <svg {...props} viewBox="0 0 24 24">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    );
  }
  return <svg {...props} viewBox="0 0 24 24"><circle cx="12" cy="12" r="2.5" /></svg>;
}

const SUMMARY_LINE_CLAMP = 3;

export function ImpactCard({
  title,
  impacts,
  summary,
  onAssetClick,
  deepDiveHref,
}: ImpactCardProps) {
  const cardType = titleCardType(title, impacts);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const shouldCollapse = summary.length > 120;
  const showExpand = shouldCollapse && !summaryExpanded;

  const cardAccent =
    cardType === "negative"
      ? SENTIMENT_NEGATIVE
      : cardType === "positive"
        ? SENTIMENT_POSITIVE
        : SENTIMENT_NEUTRAL;

  return (
    <div
      className="rounded-xl border border-white/10 bg-[#0A0F1E]/60 p-4 border-l-4"
      style={{ borderLeftColor: cardAccent }}
    >
      <div className="mb-3 flex items-center gap-2">
        <TitleIcon type={cardType} />
        <span className="text-xs font-semibold uppercase tracking-wider text-[#D4AF37]">
          {title}
        </span>
      </div>
      <div className="mb-3 flex flex-wrap gap-2">
        {impacts.map((item) => {
          const impactStyle = getImpactStyle(item.level, item.sentiment);
          return (
            <button
              key={item.symbol}
              type="button"
              onClick={() => onAssetClick?.(item.symbol)}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors hover:opacity-90 ${
                impactStyle ? "" : "text-[#9AA0A6] border-white/20 bg-white/5"
              }`}
              style={impactStyle}
            >
              <ImpactTagIcon level={item.level} sentiment={item.sentiment} />
              {item.name} ({item.levelLabel})
            </button>
          );
        })}
      </div>
      <div className="text-sm leading-relaxed text-[#E8EAED]">
        <p className={showExpand ? "line-clamp-3" : undefined}>{summary}</p>
        {showExpand && (
          <button
            type="button"
            onClick={() => setSummaryExpanded(true)}
            className="mt-1 text-xs font-medium text-[#D4AF37] hover:underline"
          >
            展开
          </button>
        )}
      </div>
      {deepDiveHref && (
        <div className="mt-3 border-t border-white/5 pt-3">
          <Link
            href={deepDiveHref}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-[#D4AF37] hover:underline"
          >
            深度分析
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      )}
    </div>
  );
}
