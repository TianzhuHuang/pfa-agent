"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { FX_REFRESH_INTERVAL } from "@/lib/refreshConstants";
import { usePageVisibility } from "@/hooks/usePageVisibility";

export type DisplayCurrency = "original" | "CNY" | "USD" | "HKD";

const STORAGE_KEY = "pfa_display_currency";

interface FxRates {
  CNY: number;
  USD: number;
  HKD: number;
  updated_at?: string | null;
}

interface DisplayCurrencyContextValue {
  displayCurrency: DisplayCurrency;
  setDisplayCurrency: (c: DisplayCurrency) => void;
  fxRates: FxRates | null;
  refreshFxRates: () => Promise<void>;
}

const defaultFx: FxRates = { CNY: 1, USD: 7.25, HKD: 0.92 };

const DisplayCurrencyContext = createContext<DisplayCurrencyContextValue | null>(null);

export function DisplayCurrencyProvider({ children }: { children: React.ReactNode }) {
  const [displayCurrency, setDisplayCurrencyState] = useState<DisplayCurrency>("CNY");
  const [fxRates, setFxRates] = useState<FxRates | null>(null);
  const visible = usePageVisibility();

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as DisplayCurrency | null;
      if (stored && ["CNY", "USD", "HKD"].includes(stored)) {
        setDisplayCurrencyState(stored);
      } else if (stored === "original") {
        setDisplayCurrencyState("CNY");
        localStorage.setItem(STORAGE_KEY, "CNY");
      }
    } catch {}
  }, []);

  const setDisplayCurrency = useCallback((c: DisplayCurrency) => {
    setDisplayCurrencyState(c);
    try {
      localStorage.setItem(STORAGE_KEY, c);
    } catch {}
  }, []);

  const refreshFxRates = useCallback(async () => {
    try {
      const { apiFetch, API_BASE } = await import("@/lib/api");
      const r = await apiFetch(`${API_BASE}/api/portfolio/fx`);
      const d = await r.json().catch(() => ({}));
      const rates = d?.rates ?? defaultFx;
      setFxRates({
        CNY: rates.CNY ?? 1,
        USD: rates.USD ?? 7.25,
        HKD: rates.HKD ?? 0.92,
        updated_at: d?.updated_at,
      });
    } catch {
      setFxRates(defaultFx);
    }
  }, []);

  useEffect(() => {
    refreshFxRates();
    if (!visible) return;
    const id = setInterval(refreshFxRates, FX_REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [refreshFxRates, visible]);

  return (
    <DisplayCurrencyContext.Provider
      value={{ displayCurrency, setDisplayCurrency, fxRates, refreshFxRates }}
    >
      {children}
    </DisplayCurrencyContext.Provider>
  );
}

export function useDisplayCurrency() {
  const ctx = useContext(DisplayCurrencyContext);
  if (!ctx) {
    return {
      displayCurrency: "CNY" as DisplayCurrency,
      setDisplayCurrency: () => {},
      fxRates: defaultFx as FxRates,
      refreshFxRates: async () => {},
    };
  }
  return ctx;
}

export function currencySymbol(c: string): string {
  return { CNY: "¥", USD: "$", HKD: "HK$" }[c] ?? c;
}
