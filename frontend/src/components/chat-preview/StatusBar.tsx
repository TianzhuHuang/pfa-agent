"use client";

import React from "react";

interface StatusBarProps {
  connected?: boolean;
  lastUpdated?: string;
}

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

export function StatusBar({ connected = true, lastUpdated }: StatusBarProps) {
  return (
    <div className="flex h-8 shrink-0 items-center justify-end gap-4 border-b border-white/5 bg-[#0A0F1E]/90 px-4 backdrop-blur-sm">
      {lastUpdated && (
        <span className="flex items-center gap-1.5 text-xs text-[#9AA0A6]" title={`更新于 ${lastUpdated}`}>
          <ClockIcon className="shrink-0" />
          {lastUpdated}
        </span>
      )}
      <span
        className="flex items-center gap-1.5 text-xs text-[#9AA0A6]"
        title={connected ? "已连接" : "离线"}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-[var(--pfa-sentiment-positive)]" : "bg-[var(--pfa-sentiment-negative)]"}`}
        />
        {connected ? "已连接" : "离线"}
      </span>
    </div>
  );
}
