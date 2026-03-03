"use client";

import React, { useState, useRef, useEffect } from "react";
import { useDisplayCurrency, currencySymbol, type DisplayCurrency } from "@/contexts/DisplayCurrencyContext";

const OPTIONS: { value: Exclude<DisplayCurrency, "original">; label: string }[] = [
  { value: "CNY", label: "人民币" },
  { value: "USD", label: "美元" },
  { value: "HKD", label: "港币" },
];

export function AccountCurrencyDropdown({
  accountId,
  value,
  onChange,
}: {
  accountId: string;
  value: Exclude<DisplayCurrency, "original">;
  onChange: (c: Exclude<DisplayCurrency, "original">) => void;
}) {
  const { fxRates } = useDisplayCurrency();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("click", onOutside);
    return () => document.removeEventListener("click", onOutside);
  }, [open]);

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="ml-1.5 inline-flex items-center rounded p-0.5 text-[#888] hover:bg-white/10 hover:text-white transition-colors"
        title="切换该账户展示币种"
      >
        <span className="text-xs">{value}</span>
        <svg
          className={`ml-0.5 h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[120px] rounded-lg border border-white/10 bg-[#0a0a0a] py-1.5 shadow-xl">
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onChange(opt.value);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-white/5"
            >
              <span className={value === opt.value ? "text-white font-medium" : "text-[#b1bad3]"}>
                {opt.label}
              </span>
              {value === opt.value && <span className="text-[#00e701] text-xs">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
