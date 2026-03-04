"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch, API_BASE } from "@/lib/api";

const CURRENCIES = ["CNY", "USD", "HKD"];

function marketToCurrency(market: string): string {
  const m = (market || "A").slice(0, 2);
  return { A: "¥", HK: "HK$", US: "$" }[m] ?? "¥";
}

function marketToExchangeLabel(market: string, marketRaw?: string): string {
  const m = (market || "A").slice(0, 2);
  if (marketRaw) return marketRaw;
  return { A: "A股", HK: "港股", US: "美股" }[m] ?? "A股";
}

interface SearchResult {
  code: string;
  name: string;
  market: string;
  market_raw?: string;
  logo_url?: string;
}

interface HoldingItem {
  symbol?: string;
  name?: string;
  market?: string;
  quantity?: number;
  cost_price?: number;
}

interface AccountItem {
  id: string;
  name: string;
  base_currency: string;
}

interface EntryModalProps {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
  initialTab?: "search" | "ocr" | "file";
}

export function EntryModal({ open, onClose, onAdded, initialTab }: EntryModalProps) {
  const [tab, setTab] = useState<"search" | "ocr" | "file">("search");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [accountList, setAccountList] = useState<AccountItem[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("默认");
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountCurrency, setNewAccountCurrency] = useState("CNY");
  const accountNames =
    accountList.length > 0
      ? accountList.map((a) => a.name).concat(["新建账户"])
      : ["默认", "新建账户"];
  const [adding, setAdding] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<SearchResult | null>(null);
  const [searchPrice, setSearchPrice] = useState("");
  const [searchQuantity, setSearchQuantity] = useState("");
  const [searchDate, setSearchDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [fxRates, setFxRates] = useState<Record<string, number>>({ CNY: 1, USD: 7.25, HKD: 0.92 });
  const quantityInputRef = useRef<HTMLInputElement>(null);

  // OCR
  const [ocrStatus, setOcrStatus] = useState("");
  const [ocrHoldings, setOcrHoldings] = useState<HoldingItem[]>([]);
  const [ocrAvailableBalance, setOcrAvailableBalance] = useState<number | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File
  const [fileStatus, setFileStatus] = useState("");
  const [fileHoldings, setFileHoldings] = useState<HoldingItem[]>([]);
  const [fileLoading, setFileLoading] = useState(false);
  const fileUploadRef = useRef<HTMLInputElement>(null);

  const loadAccounts = useCallback(async () => {
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/accounts`);
      const d = await r.json();
      const list = Array.isArray(d?.accounts) ? d.accounts : [];
      setAccountList(
        list.map((a: Record<string, unknown>) => ({
          id: String(a.id ?? a.name ?? ""),
          name: String(a.name ?? ""),
          base_currency: String(a.base_currency ?? a.currency ?? "CNY"),
        }))
      );
    } catch {
      setAccountList([]);
    }
  }, []);

  useEffect(() => {
    if (open) {
      loadAccounts();
      setOcrStatus("");
      setOcrHoldings([]);
      setOcrAvailableBalance(null);
      setFileStatus("");
      setFileHoldings([]);
      setSearchError(null);
      setSelectedItem(null);
      setSearchPrice("");
      setSearchQuantity("");
      setSearchDate(new Date().toISOString().slice(0, 10));
      if (initialTab) setTab(initialTab);
      apiFetch(`${API_BASE}/api/portfolio/fx`)
        .then((r) => r.ok ? r.json() : null)
        .then((d) => {
          if (d?.rates) setFxRates(d.rates);
        })
        .catch(() => {});
    }
  }, [open, loadAccounts, initialTab]);

  useEffect(() => {
    if (selectedItem) {
      setSearchPrice("");
      setSearchQuantity("");
      quantityInputRef.current?.focus();
    }
  }, [selectedItem]);

  useEffect(() => {
    if (selectedAccount && selectedAccount !== "新建账户") {
      const acc = accountList.find((a) => a.name === selectedAccount);
      if (acc) setNewAccountCurrency(acc.base_currency);
    }
  }, [selectedAccount, accountList]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }
    const t = setTimeout(async () => {
      try {
        setSearchError(null);
        const r = await apiFetch(`${API_BASE}/api/portfolio/search?q=${encodeURIComponent(searchQuery)}`);
        const d = await r.json();
        setSearchResults(Array.isArray(d) ? d : []);
      } catch {
        setSearchResults([]);
        setSearchError("连接失败，请确认后端已启动：uvicorn backend.main:app --port 8000");
      }
    }, 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const handleAdd = async (item: SearchResult, qty?: number, price?: number) => {
    if (adding) return;
    setAdding(item.code);
    try {
      const acc = selectedAccount === "新建账户" ? (newAccountName || "").trim() || "默认" : selectedAccount;
      const quantity = qty ?? (parseFloat(String(searchQuantity)) || 0);
      const costPrice = price ?? (parseFloat(String(searchPrice)) || 0);
      const r = await apiFetch(`${API_BASE}/api/portfolio/holdings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: item.code,
          name: item.name,
          market: item.market || "A",
          account: selectedAccount,
          new_account_name: newAccountName,
          new_account_currency: newAccountCurrency,
          quantity,
          cost_price: costPrice,
        }),
      });
      if (r.ok) {
        onAdded();
        onClose();
      }
    } finally {
      setAdding(null);
    }
  };

  const handleOcrUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setOcrLoading(true);
    setOcrStatus("识别中...（约 10–30 秒，请稍候）");
    setOcrHoldings([]);
    e.target.value = "";
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const dataUrl = reader.result as string;
        const r = await apiFetch(`${API_BASE}/api/portfolio/ocr`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contents: dataUrl }),
        });
        const blob = await r.blob();
        const text = await blob.text();
        let d: { status?: string; holdings?: unknown[]; error?: string };
        try {
          d = JSON.parse(text);
        } catch {
          setOcrStatus(r.ok ? "解析响应失败" : `服务器错误: ${text.slice(0, 150)}`);
          return;
        }
        if (d.status === "ok" && d.holdings?.length) {
          setOcrHoldings(d.holdings as HoldingItem[]);
          setOcrAvailableBalance(typeof (d as { available_balance?: number }).available_balance === "number" ? (d as { available_balance: number }).available_balance : null);
          setOcrStatus(`识别到 ${d.holdings.length} 条${(d as { available_balance?: number }).available_balance != null ? `，可用余额 ${(d as { available_balance: number }).available_balance.toLocaleString()}` : ""}，请确认后导入`);
        } else {
          setOcrStatus(d.error || "识别失败");
        }
      } catch (err) {
        setOcrStatus(`请求失败: ${(err as Error).message}`);
      } finally {
        setOcrLoading(false);
      }
    };
    reader.onerror = () => {
      setOcrStatus("文件读取失败");
      setOcrLoading(false);
    };
    reader.readAsDataURL(file);
  };

  const updateOcrHolding = (index: number, field: keyof HoldingItem, value: string | number) => {
    setOcrHoldings((prev) => {
      const next = prev.map((h, i) =>
        i === index
          ? {
              ...h,
              [field]:
                field === "quantity" || field === "cost_price"
                  ? (() => {
                      const v = parseFloat(String(value));
                      return isNaN(v) ? 0 : v;
                    })()
                  : String(value),
            }
          : h
      );
      return next;
    });
  };

  const updateFileHolding = (index: number, field: keyof HoldingItem, value: string | number) => {
    setFileHoldings((prev) => {
      const next = prev.map((h, i) =>
        i === index
          ? {
              ...h,
              [field]:
                field === "quantity" || field === "cost_price"
                  ? (() => {
                      const v = parseFloat(String(value));
                      return isNaN(v) ? 0 : v;
                    })()
                  : String(value),
            }
          : h
      );
      return next;
    });
  };

  const removeOcrHolding = (index: number) => {
    setOcrHoldings((prev) => prev.filter((_, i) => i !== index));
  };

  const removeFileHolding = (index: number) => {
    setFileHoldings((prev) => prev.filter((_, i) => i !== index));
  };

  const handleOcrConfirm = async () => {
    if (!ocrHoldings.length) return;
    setOcrLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/holdings/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          holdings: ocrHoldings,
          account: selectedAccount,
          new_account_name: newAccountName,
          new_account_currency: newAccountCurrency,
          ...(ocrAvailableBalance != null && ocrAvailableBalance > 0 && { available_balance: ocrAvailableBalance }),
        }),
      });
      if (r.ok) {
        onAdded();
        onClose();
      }
    } finally {
      setOcrLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileLoading(true);
    setFileStatus("解析中...");
    setFileHoldings([]);
    e.target.value = "";
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const dataUrl = reader.result as string;
        const b64 = dataUrl.includes(",") ? dataUrl.split(",")[1] : "";
        if (!b64) {
          setFileStatus("文件读取失败");
          return;
        }
        const r = await apiFetch(`${API_BASE}/api/portfolio/file/parse`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contents: b64, filename: file.name }),
        });
        const blob = await r.blob();
        const text = await blob.text();
        let d: { status?: string; holdings?: unknown[]; error?: string };
        try {
          d = JSON.parse(text);
        } catch {
          setFileStatus(r.ok ? "解析响应失败" : `服务器错误: ${text.slice(0, 150)}`);
          return;
        }
        if (d.status === "ok" && d.holdings?.length) {
          setFileHoldings(d.holdings as HoldingItem[]);
          setFileStatus(`解析到 ${d.holdings.length} 条，请确认后导入`);
        } else {
          setFileStatus(d.error || "解析失败");
        }
      } catch (err) {
        setFileStatus(`请求失败: ${(err as Error).message}`);
      } finally {
        setFileLoading(false);
      }
    };
    reader.onerror = () => {
      setFileStatus("文件读取失败");
      setFileLoading(false);
    };
    reader.readAsDataURL(file);
  };

  const handleFileConfirm = async () => {
    if (!fileHoldings.length) return;
    setFileLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/holdings/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          holdings: fileHoldings,
          account: selectedAccount,
          new_account_name: newAccountName,
          new_account_currency: newAccountCurrency,
        }),
      });
      if (r.ok) {
        onAdded();
        onClose();
      }
    } finally {
      setFileLoading(false);
    }
  };

  if (!open) return null;

  const tabs = [
    { id: "search" as const, label: "智能搜索" },
    { id: "ocr" as const, label: "截图识别" },
    { id: "file" as const, label: "文件导入" },
  ];

  const selectedForAdd = selectedItem ?? null;
  const priceVal = selectedForAdd ? (parseFloat(String(searchPrice)) || 0) : 0;
  const qtyVal = selectedForAdd ? (parseFloat(String(searchQuantity)) || 0) : 0;
  const market = selectedForAdd?.market || "A";
  const ccy = market === "US" ? "USD" : market === "HK" ? "HKD" : "CNY";
  const rateToCny = fxRates[ccy] ?? (ccy === "CNY" ? 1 : ccy === "USD" ? 7.25 : 0.92);
  const estimatedCny = priceVal * qtyVal * rateToCny;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="w-[95%] max-w-[560px] max-h-[90vh] overflow-y-auto rounded-xl border border-white/10 bg-[#0a0a0a]/95 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">录入持仓</h3>
          <button onClick={onClose} className="text-2xl text-[#888888] hover:text-white">
            ×
          </button>
        </div>

        {/* 账户选择 */}
        <div className="mb-4">
          <div className="mb-2 text-xs text-[#888888]">导入到账户</div>
          <div className="flex flex-wrap gap-3">
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="flex-1 min-w-[140px] rounded-lg border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white"
            >
              {accountNames.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            {selectedAccount === "新建账户" && (
              <>
                <input
                  type="text"
                  placeholder="输入新账户名称"
                  value={newAccountName}
                  onChange={(e) => setNewAccountName(e.target.value)}
                  className="flex-1 min-w-[120px] rounded-lg border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white placeholder:text-[#888888]"
                />
                <select
                  value={newAccountCurrency}
                  onChange={(e) => setNewAccountCurrency(e.target.value)}
                  className="rounded-lg border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white"
                  title="新账户默认展示币种，各标的按原始币种（如港股 HKD）自动折算"
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>
          {selectedAccount === "新建账户" && (
            <p className="mt-1 text-xs text-[#666]">
              新账户币种仅作展示基准，各标的按原始币种（如港股 HKD）自动折算
            </p>
          )}
        </div>
        <hr className="my-4 border-white/5" />

        {/* Tabs */}
        <div className="mb-4 flex gap-2 border-b border-white/5">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                tab === t.id ? "border-b-2 border-[#00e701] text-[#00e701]" : "text-[#888888] hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "search" && (
          <>
            <div className="mb-2 text-sm text-[#888888]">搜索股票代码或名称</div>
            <input
              type="text"
              placeholder="搜索股票代码、名称或加密货币（如 AAPL, 700, BTC）"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="mb-3 w-full rounded-lg border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder:text-[#888888]"
            />
            <div className="max-h-[180px] overflow-y-auto">
              {searchQuery.trim() && searchResults.length === 0 ? (
                <div className="py-3 text-sm text-[#888888]">
                  {searchError || "未找到结果"}
                </div>
              ) : (
                searchResults.map((r) => {
                  const exLabel = marketToExchangeLabel(r.market, r.market_raw);
                  const initials = (r.code || r.name || "?").slice(0, 2).toUpperCase();
                  const isSelected = selectedItem?.code === r.code;
                  return (
                    <div
                      key={r.code}
                      onClick={() => setSelectedItem(r)}
                      className={`flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-white/5 ${isSelected ? "bg-white/5 ring-1 ring-[#00e701]/50" : ""}`}
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#1a1a1a] text-xs font-medium text-[#888888]">
                        {r.logo_url ? (
                          <img src={r.logo_url} alt="" className="h-full w-full object-cover" />
                        ) : (
                          initials
                        )}
                      </div>
                      <div className="min-w-0 flex-1 text-left">
                        <div className="text-sm font-medium text-white">{r.name}</div>
                        <div className="text-xs text-[#6b7280]">
                          {r.code} · {exLabel}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedItem(r);
                        }}
                        className="text-xs text-[#00e701] hover:underline"
                      >
                        选择
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            {/* 选定后的交易表单 */}
            {selectedItem && (
              <div className="mt-4 rounded-lg border border-white/10 bg-[#111] p-4">
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{selectedItem.name}</span>
                  <span className="text-xs text-[#6b7280]">
                    {selectedItem.code} · {marketToExchangeLabel(selectedItem.market, selectedItem.market_raw)}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedItem(null)}
                    className="ml-auto text-xs text-[#888888] hover:text-white"
                  >
                    取消
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">成交单价</label>
                    <div className="flex rounded-lg border border-white/10 bg-[#1a1a1a]">
                      <span className="flex items-center px-3 text-sm text-[#888888]">
                        {marketToCurrency(selectedItem.market)}
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="0"
                        value={searchPrice}
                        onChange={(e) => setSearchPrice(e.target.value)}
                        className="flex-1 border-0 bg-transparent px-3 py-2 text-sm text-white placeholder:text-[#666] focus:outline-none"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">持仓数量</label>
                    <input
                      ref={quantityInputRef}
                      type="number"
                      step="0.0001"
                      placeholder="0"
                      value={searchQuantity}
                      onChange={(e) => setSearchQuantity(e.target.value)}
                      className="w-full rounded-lg border border-white/10 bg-[#1a1a1a] px-4 py-2 text-sm text-white placeholder:text-[#666] focus:outline-none focus:ring-1 focus:ring-[#00e701]/50"
                    />
                  </div>
                </div>
                <div className="mt-2">
                  <label className="mb-1 block text-xs text-[#888888]">交易日期</label>
                  <input
                    type="date"
                    value={searchDate}
                    onChange={(e) => setSearchDate(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-[#1a1a1a] px-4 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#00e701]/50"
                  />
                </div>
                {priceVal > 0 && qtyVal > 0 && (
                  <p className="mt-3 text-xs text-[#666]">
                    按照当前汇率，约合本币：¥ {estimatedCny.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                )}
                <button
                  onClick={() => handleAdd(selectedItem)}
                  disabled={adding === selectedItem.code}
                  className="mt-4 w-full rounded-lg bg-[#00e701] px-5 py-2.5 text-sm font-medium text-black shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow hover:shadow-[0_0_16px_rgba(34,197,94,0.4)] disabled:opacity-50"
                >
                  {adding === selectedItem.code ? "添加中..." : "添加持仓"}
                </button>
              </div>
            )}
          </>
        )}

        {tab === "ocr" && (
          <>
            <div className="mb-2 text-sm text-[#888888]">上传券商持仓截图，AI 识别后确认导入</div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleOcrUpload}
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer rounded-lg border border-dashed border-white/20 py-8 text-center text-sm text-[#888888] hover:border-[#00e701] hover:text-[#00e701]"
            >
              {ocrLoading ? "识别中..." : "拖拽上传或 点击选择"}
            </div>
            <div className="mt-2 text-sm text-[#888888]">{ocrStatus}</div>
            {ocrHoldings.length > 0 && (
              <div className="mt-3 max-h-[220px] overflow-y-auto rounded bg-[#1a1a1a] p-2">
                <div className="mb-1 grid grid-cols-[1fr_1.5fr_0.8fr_0.8fr_32px] gap-1 text-xs text-[#888888] px-1">
                  <span>代码</span>
                  <span>名称</span>
                  <span>数量</span>
                  <span>成本价</span>
                  <span />
                </div>
                {ocrHoldings.map((h, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1.5fr_0.8fr_0.8fr_32px] gap-1 items-center py-1">
                    <input
                      value={h.symbol ?? ""}
                      onChange={(e) => updateOcrHolding(i, "symbol", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666]"
                      placeholder="代码"
                    />
                    <input
                      value={h.name ?? ""}
                      onChange={(e) => updateOcrHolding(i, "name", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666]"
                      placeholder="名称"
                    />
                    <input
                      type="number"
                      value={h.quantity ?? ""}
                      onChange={(e) => updateOcrHolding(i, "quantity", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666] w-full"
                      placeholder="0"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={h.cost_price ?? ""}
                      onChange={(e) => updateOcrHolding(i, "cost_price", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666] w-full"
                      placeholder="0"
                    />
                    <button
                      type="button"
                      onClick={() => removeOcrHolding(i)}
                      className="text-[#888888] hover:text-red-400 text-lg leading-none"
                      title="删除"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            {ocrHoldings.length > 0 && (
              <button
                onClick={handleOcrConfirm}
                disabled={ocrLoading}
                className="mt-3 rounded-lg bg-[#00e701] px-5 py-2 text-sm font-medium text-black disabled:opacity-50"
              >
                确认导入
              </button>
            )}
          </>
        )}

        {tab === "file" && (
          <>
            <div className="mb-2 text-sm text-[#888888]">上传 CSV、JSON 或 Excel 文件（表头含 symbol,name,market）</div>
            <input
              ref={fileUploadRef}
              type="file"
              accept=".csv,.json,.xlsx"
              className="hidden"
              onChange={handleFileUpload}
            />
            <div
              onClick={() => fileUploadRef.current?.click()}
              className="cursor-pointer rounded-lg border border-dashed border-white/20 py-8 text-center text-sm text-[#888888] hover:border-[#00e701] hover:text-[#00e701]"
            >
              {fileLoading ? "解析中..." : "拖拽上传或 点击选择"}
            </div>
            <div className="mt-2 text-sm text-[#888888]">{fileStatus}</div>
            {fileHoldings.length > 0 && (
              <div className="mt-3 max-h-[220px] overflow-y-auto rounded bg-[#1a1a1a] p-2">
                <div className="mb-1 grid grid-cols-[1fr_1.5fr_0.8fr_0.8fr_32px] gap-1 text-xs text-[#888888] px-1">
                  <span>代码</span>
                  <span>名称</span>
                  <span>数量</span>
                  <span>成本价</span>
                  <span />
                </div>
                {fileHoldings.map((h, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1.5fr_0.8fr_0.8fr_32px] gap-1 items-center py-1">
                    <input
                      value={h.symbol ?? ""}
                      onChange={(e) => updateFileHolding(i, "symbol", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666]"
                      placeholder="代码"
                    />
                    <input
                      value={h.name ?? ""}
                      onChange={(e) => updateFileHolding(i, "name", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666]"
                      placeholder="名称"
                    />
                    <input
                      type="number"
                      value={h.quantity ?? ""}
                      onChange={(e) => updateFileHolding(i, "quantity", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666] w-full"
                      placeholder="0"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={h.cost_price ?? ""}
                      onChange={(e) => updateFileHolding(i, "cost_price", e.target.value)}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white placeholder:text-[#666] w-full"
                      placeholder="0"
                    />
                    <button
                      type="button"
                      onClick={() => removeFileHolding(i)}
                      className="text-[#888888] hover:text-red-400 text-lg leading-none"
                      title="删除"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            {fileHoldings.length > 0 && (
              <button
                onClick={handleFileConfirm}
                disabled={fileLoading}
                className="mt-3 rounded-lg bg-[#00e701] px-5 py-2 text-sm font-medium text-black disabled:opacity-50"
              >
                确认导入
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
