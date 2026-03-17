"use client";

import React from "react";

export interface ChatSessionItem {
  id: string;
  firstQuestion: string;
  emotionTag: string;
  updatedAt: string;
  sentiment?: "positive" | "negative" | "neutral";
}

interface ChatHistorySidebarProps {
  sessions: ChatSessionItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

function inferSentiment(emotionTag: string): "positive" | "negative" | "neutral" {
  const t = emotionTag;
  if (/负面|利空|风险|警告|下跌|熊|空/.test(t)) return "negative";
  if (/正面|利好|机会|上涨|牛|多/.test(t)) return "positive";
  return "neutral";
}

function SentimentIcon({ sentiment }: { sentiment: "positive" | "negative" | "neutral" }) {
  const base = "h-3.5 w-3.5 shrink-0";
  const positiveClass = `${base} text-[var(--pfa-sentiment-positive)]`;
  const negativeClass = `${base} text-[var(--pfa-sentiment-negative)]`;
  const neutralClass = `${base} text-[var(--pfa-sentiment-neutral)]`;
  const stroke = "currentColor";
  const strokeWidth = 2;

  if (sentiment === "positive") {
    return (
      <svg className={positiveClass} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M12 19V5M5 12l7-7 7 7" />
      </svg>
    );
  }
  if (sentiment === "negative") {
    return (
      <svg className={negativeClass} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M12 5v14M5 12l7 7 7-7" />
      </svg>
    );
  }
  return (
    <svg className={neutralClass} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

export function ChatHistorySidebar({
  sessions,
  activeId,
  onSelect,
}: ChatHistorySidebarProps) {
  return (
    <div className="flex h-full flex-col border-r border-white/5 bg-[#0A0F1E]/70">
      <div className="border-b border-white/5 px-3 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#9AA0A6]">
          对话历史
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <div className="py-6 text-center text-xs text-[#6B7280]">
            暂无记录
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((s) => {
              const sentiment = s.sentiment ?? inferSentiment(s.emotionTag);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onSelect(s.id)}
                  title={s.firstQuestion}
                  className={`group flex w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left transition-colors ${
                    activeId === s.id
                      ? "bg-[#D4AF37]/15 text-white border border-[#D4AF37]/30"
                      : "text-[#9AA0A6] hover:bg-white/5 hover:text-white border border-transparent"
                  }`}
                >
                  <span className="mt-0.5 shrink-0">
                    <SentimentIcon sentiment={sentiment} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium leading-snug line-clamp-2 truncate">
                      {s.emotionTag}
                    </div>
                    <div className="mt-1 flex items-center gap-1 text-[10px] text-[#6B7280]">
                      <ClockIcon className="shrink-0" />
                      <span>{s.updatedAt}</span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
