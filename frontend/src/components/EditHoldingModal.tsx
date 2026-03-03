"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { useDisplayCurrency } from "@/contexts/DisplayCurrencyContext";

interface SearchResult {
  code: string;
  name: string;
  market: string;
  market_raw?: string;
}

const CURRENCIES = ["CNY", "USD", "HKD"] as const;

function inferCurrencyFromSymbol(sym: string, existingMarket?: string): "CNY" | "USD" | "HKD" | null {
  const s = sym.trim();
  if (!s) return null;
  if (/^[A-Za-z][A-Za-z0-9.]*$/.test(s)) return "USD";
  if (/^\d+$/.test(s)) {
    if (s.length === 5 && s.startsWith("0")) return "HKD";
    if (s.length >= 3 && s.length <= 4) return "HKD";
    if (s.length === 6 && s.startsWith("6")) return "CNY";
    if (s.length === 6 && (s.startsWith("0") || s.startsWith("3"))) return "CNY";
  }
  if (existingMarket === "HK") return "HKD";
  if (existingMarket === "A") return "CNY";
  if (existingMarket === "US") return "USD";
  return null;
}
const EXCHANGES = [
  { value: "", label: "自动推断" },
  { value: "SSE", label: "上交所" },
  { value: "SZSE", label: "深交所" },
  { value: "NYSE", label: "纽交所" },
  { value: "NASDAQ", label: "纳斯达克" },
  { value: "HKEX", label: "港交所" },
  { value: "SGX", label: "新交所" },
  { value: "OTHER", label: "其他" },
];

interface HoldingRow {
  symbol?: string;
  name?: string;
  currency?: string;
  cost_price?: number;
  quantity?: number;
  market?: string;
  exchange?: string;
  account?: string;
  source?: string;
}

interface EditHoldingModalProps {
  open: boolean;
  holding: HoldingRow | null;
  onClose: () => void;
  onSaved: () => void;
}

export function EditHoldingModal({ open, holding, onClose, onSaved }: EditHoldingModalProps) {
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [market, setMarket] = useState("A");
  const [quantity, setQuantity] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [currency, setCurrency] = useState<"CNY" | "USD" | "HKD">("CNY");
  const [exchange, setExchange] = useState("");
  const [account, setAccount] = useState("默认");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [symbolSearchResults, setSymbolSearchResults] = useState<SearchResult[]>([]);
  const [symbolSearching, setSymbolSearching] = useState(false);
  const symbolSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { fxRates } = useDisplayCurrency();

  useEffect(() => {
    if (open && holding) {
      setSymbol(holding.symbol ?? "");
      setName(holding.name ?? "");
      setMarket(holding.market ?? "A");
      setQuantity(String(holding.quantity ?? ""));
      setCostPrice(String(holding.cost_price ?? ""));
      setCurrency((holding.currency as "CNY" | "USD" | "HKD") || "CNY");
      setExchange(holding.exchange ?? "");
      setAccount(holding.account ?? "默认");
      setError(null);
    }
  }, [open, holding]);

  useEffect(() => {
    if (!open) return;
    const inferred = inferCurrencyFromSymbol(symbol, market);
    if (inferred) setCurrency(inferred);
  }, [symbol, open, market]);

  useEffect(() => {
    if (!open) return;
    const s = symbol.trim();
    // 与 EntryModal 一致：任意 2 字及以上即触发搜索（支持代码、中文名、拼音、混合输入）
    const shouldSearch = s.length >= 2;
    if (!shouldSearch) {
      setSymbolSearchResults([]);
      return;
    }
    if (symbolSearchRef.current) clearTimeout(symbolSearchRef.current);
    symbolSearchRef.current = setTimeout(async () => {
      setSymbolSearching(true);
      try {
        const r = await apiFetch(`${API_BASE}/api/portfolio/search?q=${encodeURIComponent(s)}`);
        const d = await r.json();
        const list = Array.isArray(d) ? d : [];
        setSymbolSearchResults(list);
        const norm = (c: string) => (c || "").replace(/\.(SH|SZ|HK)$/i, "").toUpperCase();
        const exact = list.find((x: SearchResult) => norm(x.code) === s.toUpperCase() || norm(x.code) === s);
        const pick = exact || (list.length === 1 ? list[0] : null);
        if (pick) {
          setName(pick.name || "");
          setMarket(pick.market || "A");
          const inf = inferCurrencyFromSymbol(pick.code, pick.market);
          if (inf) setCurrency(inf);
        }
      } catch {
        setSymbolSearchResults([]);
      } finally {
        setSymbolSearching(false);
        symbolSearchRef.current = null;
      }
    }, 400);
    return () => {
      if (symbolSearchRef.current) clearTimeout(symbolSearchRef.current);
    };
  }, [symbol, open]);

  const handleSave = async () => {
    if (!symbol.trim()) {
      setError("标的代码不能为空");
      return;
    }
    setSaving(true);
    setError(null);
    const origSymbol = (holding?.symbol ?? "").trim();
    const newSym = symbol.trim();
    const isSymbolChange = origSymbol && newSym !== origSymbol;
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/holdings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: isSymbolChange ? origSymbol : newSym,
          account: account.trim() || "默认",
          ...(isSymbolChange && { new_symbol: newSym }),
          quantity: quantity ? parseFloat(quantity) : undefined,
          cost_price: costPrice ? parseFloat(costPrice) : undefined,
          currency: currency || undefined,
          market: market || undefined,
          exchange: exchange.trim() || undefined,
          name: name.trim() || undefined,
        }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || `保存失败 ${r.status}`);
      }
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!holding?.symbol?.trim() || !confirm(`确定删除 ${holding.name || holding.symbol} 的持仓记录？`)) return;
    setDeleting(true);
    setError(null);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/trade/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "remove",
          symbol: holding.symbol.trim(),
          name: holding.name ?? "",
          market: holding.market ?? "A",
          quantity: 0,
          cost_price: 0,
          account: (holding.account ?? "默认").trim() || "默认",
        }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || d.error || `删除失败 ${r.status}`);
      }
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl border border-white/10 bg-[#0a0a0a] p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">编辑持仓</h3>
          <button
            onClick={onClose}
            className="rounded p-1.5 text-[#888888] hover:bg-white/10 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/20 px-3 py-2 text-sm text-[#ff4e33]">{error}</div>
        )}

        <div className="space-y-4">
          <div className="relative">
            <label className="mb-1 block text-xs text-[#888888]">标的代码</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666]"
              placeholder="如 NIO、600519、000858"
            />
            {symbolSearching && (
              <span className="absolute right-3 top-8 text-xs text-[#666]">搜索中...</span>
            )}
            {symbolSearchResults.length >= 1 && !symbolSearching && (
              <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-40 overflow-y-auto rounded-lg border border-white/10 bg-[#0a0a0a] py-1 shadow-xl">
                {symbolSearchResults.map((item) => (
                  <button
                    key={`${item.code}-${item.name}`}
                    type="button"
                    onClick={() => {
                      setSymbol(item.code);
                      setName(item.name || "");
                      setMarket(item.market || "A");
                      const inf = inferCurrencyFromSymbol(item.code, item.market);
                      if (inf) setCurrency(inf);
                      setSymbolSearchResults([]);
                    }}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-white/5"
                  >
                    <span className="text-white">{item.name || item.code}</span>
                    <span className="text-[#888]">{item.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#888888]">标的名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666]"
              placeholder="可选"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#888888]">持仓数量</label>
            <input
              type="number"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666]"
              placeholder="0"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#888888]">买入成本</label>
            <input
              type="number"
              step="any"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white placeholder:text-[#666]"
              placeholder="0"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#888888]">原始币种</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as "CNY" | "USD" | "HKD")}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white"
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c} className="bg-[#0a0a0a]">
                  {c === "CNY" ? "人民币 (CNY)" : c === "USD" ? "美元 (USD)" : "港币 (HKD)"}
                </option>
              ))}
            </select>
            {costPrice && parseFloat(costPrice) > 0 && currency !== "CNY" && (
              <p className="mt-1 text-xs text-[#666]">
                当前汇率：1 {currency} ≈ {(currency === "HKD" ? (fxRates?.HKD ?? 0.92) : (fxRates?.USD ?? 7.25)).toFixed(2)} CNY，
                折算约 ¥{(parseFloat(costPrice) * (currency === "HKD" ? (fxRates?.HKD ?? 0.92) : (fxRates?.USD ?? 7.25))).toFixed(2)}
              </p>
            )}
            <p className="mt-1 text-xs text-[#666]">根据代码自动推断，市值按首页切换币种统一折算</p>
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#888888]">交易所</label>
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white"
            >
              {EXCHANGES.map((x) => (
                <option key={x.value || "auto"} value={x.value} className="bg-[#0a0a0a]">
                  {x.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-[#666]">T14 等多地上市标的可手动选择正确交易所</p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={handleSave}
            disabled={saving || deleting || !symbol.trim()}
            className="flex-1 rounded-lg bg-[#00e701] py-2.5 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "保存中..." : "保存"}
          </button>
          <button
            onClick={onClose}
            disabled={saving || deleting}
            className="rounded-lg border border-white/20 px-4 py-2.5 text-sm font-medium text-white hover:bg-white/5 disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleDelete}
            disabled={saving || deleting}
            className="rounded-lg border border-red-500/50 bg-red-500/20 px-4 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/30 disabled:opacity-50"
          >
            {deleting ? "删除中..." : "删除"}
          </button>
        </div>
      </div>
    </div>
  );
}
