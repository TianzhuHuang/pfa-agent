"use client";

import React, { useState, useRef, useEffect } from "react";
import { useDisplayCurrency, currencySymbol, type DisplayCurrency } from "@/contexts/DisplayCurrencyContext";

const OPTIONS: { value: Exclude<DisplayCurrency, "original">; label: string }[] = [
  { value: "CNY", label: "人民币 (CNY)" },
  { value: "USD", label: "美元 (USD)" },
  { value: "HKD", label: "港币 (HKD)" },
];

export function CurrencyDropdown({ compact = false }: { compact?: boolean }) {
  const { displayCurrency, setDisplayCurrency, fxRates } = useDisplayCurrency();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("click", onOutside);
    return () => document.removeEventListener("click", onOutside);
  }, [open]);

  const effectiveCur = displayCurrency === "original" ? "CNY" : displayCurrency;
  const sym = currencySymbol(effectiveCur);
  const rates = fxRates ?? { CNY: 1, USD: 7.25, HKD: 0.92 };

  const getRateHint = (opt: string) => {
    if (opt === effectiveCur) return null;
    const rTo = Number(rates[opt as keyof typeof rates]);
    const rFrom = Number(rates[effectiveCur as keyof typeof rates] ?? 1);
    if (!rTo || rTo <= 0 || !rFrom) return null;
    const cross = rFrom / rTo;
    return `1 ${effectiveCur} ≈ ${cross.toFixed(2)} ${opt}`;
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-white hover:bg-white/10 transition-colors"
      >
        <span>
          {compact ? sym : `账户总值 (${effectiveCur})`}
        </span>
        <svg
          className={`h-4 w-4 text-[#888] transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[200px] rounded-lg border border-white/10 bg-[#0a0a0a] py-2 shadow-xl">
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                setDisplayCurrency(opt.value);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-white/5 transition-colors"
            >
              <span className={effectiveCur === opt.value ? "text-white font-medium" : "text-[#b1bad3]"}>
                {opt.label}
              </span>
              {effectiveCur === opt.value && (
                <span className="text-[#00e701]">✓</span>
              )}
              {effectiveCur !== opt.value && getRateHint(opt.value) && (
                <span className="text-xs text-[#666] ml-2">{getRateHint(opt.value)}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
