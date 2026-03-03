"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

/** 涨跌颜色方案：green_up=绿涨红跌（国际），red_up=红涨绿跌（A股） */
export type ColorSchemeMode = "green_up" | "red_up";

const STORAGE_KEY = "pfa_color_scheme";

interface ColorSchemeContextValue {
  mode: ColorSchemeMode;
  setMode: (m: ColorSchemeMode) => void;
  /** 涨时的文字颜色 class */
  upColor: string;
  /** 跌时的文字颜色 class */
  downColor: string;
  /** 涨时的背景+文字 class（用于 badge） */
  upBadge: string;
  /** 跌时的背景+文字 class（用于 badge） */
  downBadge: string;
  /** 涨时的 hex（用于 chart fill 等） */
  upHex: string;
  /** 跌时的 hex */
  downHex: string;
}

const ColorSchemeContext = createContext<ColorSchemeContextValue | null>(null);

const GREEN = "#00e701";
const RED = "#ff4e33";

export function ColorSchemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ColorSchemeMode>("green_up");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as ColorSchemeMode | null;
      if (stored === "green_up" || stored === "red_up") {
        setModeState(stored);
      }
    } catch {}
  }, []);

  const setMode = useCallback((m: ColorSchemeMode) => {
    setModeState(m);
    try {
      localStorage.setItem(STORAGE_KEY, m);
    } catch {}
  }, []);

  useEffect(() => {
    const isRedUp = mode === "red_up";
    document.documentElement.style.setProperty("--pfa-up", isRedUp ? RED : GREEN);
    document.documentElement.style.setProperty("--pfa-down", isRedUp ? GREEN : RED);
  }, [mode]);

  const isRedUp = mode === "red_up";
  const upColor = isRedUp ? "text-[#ff4e33]" : "text-[#00e701]";
  const downColor = isRedUp ? "text-[#00e701]" : "text-[#ff4e33]";
  const upBadge = isRedUp ? "bg-red-500/20 text-[#ff4e33]" : "bg-green-500/20 text-[#00e701]";
  const downBadge = isRedUp ? "bg-green-500/20 text-[#00e701]" : "bg-red-500/20 text-[#ff4e33]";
  const upHex = isRedUp ? RED : GREEN;
  const downHex = isRedUp ? GREEN : RED;

  return (
    <ColorSchemeContext.Provider
      value={{ mode, setMode, upColor, downColor, upBadge, downBadge, upHex, downHex }}
    >
      {children}
    </ColorSchemeContext.Provider>
  );
}

export function useColorScheme() {
  const ctx = useContext(ColorSchemeContext);
  if (!ctx) {
    return {
      mode: "green_up" as ColorSchemeMode,
      setMode: () => {},
      upColor: "text-[#00e701]",
      downColor: "text-[#ff4e33]",
      upBadge: "bg-green-500/20 text-[#00e701]",
      downBadge: "bg-red-500/20 text-[#ff4e33]",
      upHex: GREEN,
      downHex: RED,
    };
  }
  return ctx;
}
