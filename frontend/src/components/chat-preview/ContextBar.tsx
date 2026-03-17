"use client";

import React from "react";

export interface HoldingTag {
  symbol: string;
  name: string;
  industry: string;
  /** 是否正在被 AI 分析（显示呼吸灯） */
  active?: boolean;
}

interface ContextBarProps {
  tags: HoldingTag[];
  onTagClick?: (tag: HoldingTag) => void;
}

export function ContextBar({ tags, onTagClick }: ContextBarProps) {
  if (tags.length === 0) {
    return (
      <div className="flex h-[60px] items-center justify-center border-b border-white/5 bg-[#0A0F1E]/80 backdrop-blur-md">
        <span className="text-sm text-[#9AA0A6]">暂无持仓，请先录入</span>
      </div>
    );
  }

  return (
    <div className="flex h-[60px] shrink-0 items-center gap-2 overflow-x-auto border-b border-white/5 bg-[#0A0F1E]/80 px-4 backdrop-blur-md">
      {tags.map((tag) => (
        <button
          key={tag.symbol}
          type="button"
          onClick={() => onTagClick?.(tag)}
          className="group relative flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-white/90 transition-colors hover:bg-white/5"
        >
          <span className="font-medium">{tag.name}</span>
          <span className="text-[#9AA0A6]">·</span>
          <span className="text-xs text-[#9AA0A6]">{tag.industry}</span>
          {tag.active && (
            <span
              className="absolute bottom-0 left-1/2 h-0.5 w-4/5 -translate-x-1/2 rounded-full bg-[#D4AF37] animate-pulse"
              style={{ boxShadow: "0 0 8px rgba(212,175,55,0.6)" }}
            />
          )}
        </button>
      ))}
    </div>
  );
}
