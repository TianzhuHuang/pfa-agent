"use client";

import React from "react";
import { useColorScheme } from "@/contexts/ColorSchemeContext";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { motion } from "framer-motion";

const ALLOCATION_COLORS = [
  "#1976d2",
  "#2e7d32",
  "#ed6c02",
  "#7b1fa2",
  "#00838f",
  "#5d4037",
  "#455a64",
  "#757575",
];

function currencySymbol(c: string): string {
  return { CNY: "¥", USD: "$", HKD: "HK$" }[c] ?? c;
}

interface HoldingForChart {
  symbol?: string;
  name?: string;
  account?: string;
  value_cny?: number;
  value_local?: number;
  value_display?: number | null;
  currency_error?: boolean;
  today_pnl?: number;
  today_pct?: number;
  pnl_cny?: number;
  currency?: string;
  is_cash?: boolean;
  accounts?: string[];
}

interface PortfolioChartsProps {
  byAccount: Record<string, { holdings: HoldingForChart[]; value?: number; value_cny?: number }>;
  totalValue: number;
  targetCurrency: string;
  loading?: boolean;
  selectedAccount: string | null;
  pnlMode: "today" | "cumulative";
  onAccountChange: (account: string | null) => void;
  onPnlModeChange: (mode: "today" | "cumulative") => void;
}

function aggregateBySymbol(holdings: HoldingForChart[]): HoldingForChart[] {
  const grouped = holdings
    .filter((h) => !h.currency_error && !h.is_cash)
    .reduce<Record<string, HoldingForChart>>((acc, h) => {
      const key = (h.symbol ?? "").trim() || "CASH";
      if (!acc[key]) {
        acc[key] = {
          ...h,
          value_cny: 0,
          today_pnl: 0,
          pnl_cny: 0,
          accounts: [],
        };
      }
      acc[key].value_cny = (acc[key].value_cny ?? 0) + (h.value_cny ?? h.value_local ?? 0);
      acc[key].today_pnl = (acc[key].today_pnl ?? 0) + (h.today_pnl ?? 0);
      acc[key].pnl_cny = (acc[key].pnl_cny ?? 0) + (h.pnl_cny ?? 0);
      if (h.account && !acc[key].accounts?.includes(h.account)) {
        acc[key].accounts = [...(acc[key].accounts ?? []), h.account];
      }
      return acc;
    }, {});
  return Object.values(grouped);
}

function AllocationDonut({
  holdings,
  totalValue,
  targetCurrency,
  loading,
}: {
  holdings: HoldingForChart[];
  totalValue: number;
  targetCurrency: string;
  loading?: boolean;
}) {
  const sym = targetCurrency === "original" ? "¥" : currencySymbol(targetCurrency);
  const sorted = [...holdings]
    .filter((h) => !h.currency_error && (h.value_cny ?? h.value_local ?? 0) > 0)
    .sort((a, b) => (b.value_cny ?? b.value_local ?? 0) - (a.value_cny ?? a.value_local ?? 0));

  const top5 = sorted.slice(0, 5);
  const otherVal = sorted.slice(5).reduce((s, h) => s + (h.value_cny ?? h.value_local ?? 0), 0);
  const chartData = top5.map((h, idx) => ({
    id: `${h.symbol ?? ""}-${idx}`,
    name: (h.name || h.symbol || "?")?.slice(0, 6),
    value: h.value_cny ?? h.value_local ?? 0,
    fullName: h.name || h.symbol,
    accounts: h.accounts,
  }));
  if (otherVal > 0) {
    chartData.push({ id: "other", name: "其他", value: otherVal, fullName: "其他", accounts: undefined });
  }

  if (loading || chartData.length === 0) {
    return (
      <div className="flex min-h-[260px] flex-col items-center justify-center gap-2 rounded-lg bg-[#0a0a0a]">
        <div className="text-5xl opacity-15">🐢</div>
        <span className="text-xs text-[#666]">暂无持仓数据</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-[#0a0a0a] p-4 min-w-0">
      <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888888]">
        仓位分布
      </div>
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="h-[200px] w-full max-w-[200px] sm:h-[260px] sm:w-[200px] shrink-0 mx-auto sm:mx-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius="45%"
                outerRadius="65%"
                paddingAngle={1}
                dataKey="value"
                animationDuration={400}
                animationBegin={0}
              >
                {chartData.map((_, i) => (
                  <Cell key={i} fill={ALLOCATION_COLORS[i % ALLOCATION_COLORS.length]} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                }}
                labelStyle={{ color: "#888" }}
                formatter={(val: number | undefined) => [`${sym}${(val ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, ""]}
                labelFormatter={(_, payload) => {
                  const p = Array.isArray(payload) ? payload[0]?.payload : undefined;
                  const label = p?.fullName ?? "";
                  const accts = p?.accounts as string[] | undefined;
                  if (accts && accts.length > 1) return `${label} (${accts.join("、")})`;
                  return label;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-1 flex-col gap-1 text-xs">
          <div className="mb-2 text-center text-lg font-semibold text-white">
            {sym}
            {totalValue >= 10000
              ? `${(totalValue / 10000).toFixed(1)}万`
              : totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          {chartData.slice(0, 5).map((d, i) => (
            <div key={d.id ?? i} className="flex items-center gap-2">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: ALLOCATION_COLORS[i % ALLOCATION_COLORS.length] }}
              />
              <span className="truncate text-[#b1bad3]">{d.fullName || d.name}</span>
            </div>
          ))}
          {chartData.length > 5 && (
            <div className="flex items-center gap-2">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: ALLOCATION_COLORS[5] }}
              />
              <span className="text-[#b1bad3]">其他</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PnlBarChart({
  holdings,
  targetCurrency,
  pnlMode,
  loading,
}: {
  holdings: HoldingForChart[];
  targetCurrency: string;
  pnlMode: "today" | "cumulative";
  loading?: boolean;
}) {
  const sym = targetCurrency === "original" ? "¥" : currencySymbol(targetCurrency);
  const { upHex, downHex } = useColorScheme();
  const data = holdings
    .filter((h) => ((pnlMode === "today" ? h.today_pnl : h.pnl_cny) ?? 0) !== 0)
    .sort((a, b) => ((pnlMode === "today" ? b.today_pnl : b.pnl_cny) ?? 0) - ((pnlMode === "today" ? a.today_pnl : a.pnl_cny) ?? 0))
    .slice(0, 10)
    .map((h) => ({
      name: (h.name || h.symbol || "?")?.slice(0, 6),
      pnl: (pnlMode === "today" ? h.today_pnl : h.pnl_cny) ?? 0,
      fullName: h.name || h.symbol,
      accounts: h.accounts,
    }));

  const label = pnlMode === "today" ? "今日盈亏" : "累计盈亏";
  const emptyMsg = pnlMode === "today" ? "暂无今日盈亏数据" : "暂无累计盈亏数据";

  if (loading || data.length === 0) {
    return (
      <div className="flex min-h-[260px] flex-col items-center justify-center gap-2 rounded-lg bg-[#0a0a0a]">
        <div className="text-5xl opacity-15">🐢</div>
        <span className="text-xs text-[#666]">{emptyMsg}</span>
      </div>
    );
  }

  const maxAbs = Math.max(...data.map((d) => Math.abs(d.pnl)), 1);

  return (
    <div className="rounded-lg bg-[#0a0a0a] p-4 min-w-0">
      <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#888888]">
        {label}
      </div>
      <div className="h-[200px] sm:h-[260px] min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 20, left: 4, bottom: 4 }}
          >
            <XAxis
              type="number"
              hide
              domain={[-maxAbs * 1.1, maxAbs * 1.1]}
            />
            <ReferenceLine x={0} stroke="#444" strokeWidth={1} />
            <YAxis
              type="category"
              dataKey="name"
              width={56}
              tick={{ fill: "#888", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1a1a1a",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
              }}
              formatter={(val: number | undefined) => [
                `${(val ?? 0) >= 0 ? "+" : ""}${sym}${(val ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                label,
              ]}
              labelFormatter={(_, payload) => {
                const p = Array.isArray(payload) ? payload[0]?.payload : undefined;
                const name = p?.fullName ?? "";
                const accts = p?.accounts as string[] | undefined;
                if (accts && accts.length > 1) return `${name} (${accts.join("、")})`;
                return name;
              }}
            />
            <Bar
              dataKey="pnl"
              radius={[0, 2, 2, 0]}
              maxBarSize={16}
              animationDuration={400}
              animationBegin={0}
            >
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={data[i].pnl >= 0 ? upHex : downHex}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function PortfolioCharts({
  byAccount,
  totalValue,
  targetCurrency,
  loading,
  selectedAccount,
  pnlMode,
  onAccountChange,
  onPnlModeChange,
}: PortfolioChartsProps) {
  const accountNames = Object.keys(byAccount ?? {});
  const filteredHoldings: HoldingForChart[] = [];
  if (selectedAccount === "all" || selectedAccount === null || !selectedAccount) {
    for (const data of Object.values(byAccount ?? {})) {
      filteredHoldings.push(...(data.holdings ?? []));
    }
  } else if (byAccount?.[selectedAccount]) {
    filteredHoldings.push(...(byAccount[selectedAccount].holdings ?? []));
  }
  const aggregated = aggregateBySymbol(filteredHoldings);

  const filteredTotal =
    selectedAccount === "all" || selectedAccount === null || !selectedAccount
      ? totalValue
      : (byAccount?.[selectedAccount]?.value ?? byAccount?.[selectedAccount]?.value_cny ?? 0);

  return (
    <motion.div
      className="min-h-[200px] sm:min-h-[300px] sm:max-h-[350px] w-full overflow-visible relative z-0"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 筛选器：账户 Tabs + 盈亏切换 */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => onAccountChange("all")}
            className={`rounded px-3 py-1.5 text-sm transition ${
              (selectedAccount === "all" || selectedAccount === null || !selectedAccount)
                ? "bg-white/15 text-white"
                : "bg-white/5 text-[#888] hover:bg-white/10 hover:text-[#b1bad3]"
            }`}
          >
            全部账户
          </button>
          {accountNames.map((acct) => (
            <button
              key={acct}
              onClick={() => onAccountChange(acct)}
              className={`rounded px-3 py-1.5 text-sm transition ${
                selectedAccount === acct
                  ? "bg-white/15 text-white"
                  : "bg-white/5 text-[#888] hover:bg-white/10 hover:text-[#b1bad3]"
              }`}
            >
              {acct}
            </button>
          ))}
        </div>
        <div className="flex rounded bg-white/5 p-0.5">
          <button
            onClick={() => onPnlModeChange("today")}
            className={`rounded px-2.5 py-1 text-xs transition ${
              pnlMode === "today" ? "bg-white/15 text-white" : "text-[#888] hover:text-[#b1bad3]"
            }`}
          >
            今日盈亏
          </button>
          <button
            onClick={() => onPnlModeChange("cumulative")}
            className={`rounded px-2.5 py-1 text-xs transition ${
              pnlMode === "cumulative" ? "bg-white/15 text-white" : "text-[#888] hover:text-[#b1bad3]"
            }`}
          >
            累计盈亏
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 w-full min-w-0 [&>*]:min-h-0">
        <div className="min-w-0">
          <AllocationDonut
            holdings={aggregated}
            totalValue={filteredTotal}
            targetCurrency={targetCurrency}
            loading={loading}
          />
        </div>
        <div className="min-w-0">
          <PnlBarChart
            holdings={aggregated}
            targetCurrency={targetCurrency}
            pnlMode={pnlMode}
            loading={loading}
          />
        </div>
      </div>
    </motion.div>
  );
}
