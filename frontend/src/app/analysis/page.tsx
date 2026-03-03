"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
} from "recharts";
import { apiFetch, API_BASE } from "@/lib/api";
import { useDisplayCurrency, currencySymbol } from "@/contexts/DisplayCurrencyContext";
import { CurrencyDropdown } from "@/components/CurrencyDropdown";

const CHART_COLORS = ["#1976d2", "#2e7d32", "#ed6c02", "#7b1fa2", "#00838f"];
const MARKET_LABELS: Record<string, string> = { A: "A股", HK: "港股", US: "美股", OTHER: "其他" };

export default function AnalysisPage() {
  const { displayCurrency } = useDisplayCurrency();
  const [val, setVal] = useState<{
    by_account?: Record<string, { holdings: { symbol?: string; name?: string; value_cny?: number }[]; value?: number }>;
    by_market?: Record<string, { value: number; count: number }>;
    total_value_cny?: number;
    target_currency?: string;
    fx_rates?: Record<string, number>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`)
      .then((r) => r.json())
      .then(setVal)
      .catch(() => setVal(null))
      .finally(() => setLoading(false));
  }, [displayCurrency]);

  useEffect(() => {
    setLoading(true);
    refresh();
  }, [refresh]);

  const targetCur = val?.target_currency ?? displayCurrency;
  const sym = targetCur === "original" ? "¥" : currencySymbol(targetCur);

  const marketData = val?.by_market
    ? Object.entries(val.by_market)
        .filter(([, d]) => d.value > 0)
        .map(([mkt, d]) => ({ name: MARKET_LABELS[mkt] || mkt, value: d.value, count: d.count }))
        .sort((a, b) => b.value - a.value)
    : [];

  const allHoldings: { name: string; value: number }[] = [];
  for (const data of Object.values(val?.by_account ?? {})) {
    for (const h of data.holdings ?? []) {
      const v = h.value_cny ?? 0;
      if (v > 0) allHoldings.push({ name: (h.name || h.symbol || "?")?.slice(0, 6), value: v });
    }
  }
  const allocationData = allHoldings
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)
    .map((d) => ({ ...d, name: d.name || "?" }));

  const totalV = val?.total_value_cny ?? 0;
  const topHoldingPct = totalV > 0 && allocationData[0] ? (allocationData[0].value / totalV) * 100 : 0;
  const riskData = [
    { subject: "集中度", value: Math.min(100, topHoldingPct * 2), fullMark: 100 },
    { subject: "分散度", value: Math.min(100, (allocationData.length / 10) * 100), fullMark: 100 },
    { subject: "流动性", value: 75, fullMark: 100 },
    { subject: "估值", value: 50, fullMark: 100 },
    { subject: "波动", value: 40, fullMark: 100 },
  ];

  return (
    <div className="mx-auto max-w-6xl p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-xl font-semibold text-white">深度分析</h1>
          <CurrencyDropdown />
        </div>

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-32 animate-pulse rounded bg-white/10" />
          </div>
        ) : !val?.by_account || Object.keys(val.by_account).length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-4 py-20">
            <div className="text-5xl opacity-20">📊</div>
            <p className="text-sm text-[#666]">暂无持仓数据，请先在 Portfolio 录入</p>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid gap-8 sm:grid-cols-2"
          >
            {/* 市场分布 */}
            <div className="rounded-lg bg-[#0a0a0a] p-4">
              <div className="mb-4 text-xs font-medium uppercase tracking-wider text-[#888888]">
                市场分布
              </div>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={marketData} layout="vertical" margin={{ top: 4, right: 20, left: 60, bottom: 4 }}>
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" width={50} tick={{ fill: "#888", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                      formatter={(v: number | undefined) => [`${sym}${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, "市值"]}
                    />
                    <Bar dataKey="value" fill="#1976d2" radius={[0, 2, 2, 0]} maxBarSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* 仓位分布 */}
            <div className="rounded-lg bg-[#0a0a0a] p-4">
              <div className="mb-4 text-xs font-medium uppercase tracking-wider text-[#888888]">
                仓位分布
              </div>
              <div className="flex items-center gap-4">
                <div className="h-[180px] w-[180px] shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={allocationData}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {allocationData.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} stroke="none" />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                        formatter={(v: number | undefined) => [`${sym}${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, ""]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="text-lg font-semibold text-white">
                  {sym}
                  {totalV >= 10000 ? `${(totalV / 10000).toFixed(1)}万` : totalV.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
              </div>
            </div>

            {/* 风险因子雷达 */}
            <div className="sm:col-span-2 rounded-lg bg-[#0a0a0a] p-4">
              <div className="mb-4 text-xs font-medium uppercase tracking-wider text-[#888888]">
                风险因子
              </div>
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={riskData}>
                    <PolarGrid stroke="#333" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: "#888", fontSize: 11 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#666" }} />
                    <Radar name="风险" dataKey="value" stroke="#1976d2" fill="#1976d2" fillOpacity={0.3} strokeWidth={2} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </motion.div>
        )}
      </div>
  );
}
