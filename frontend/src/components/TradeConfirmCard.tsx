"use client";

import React, { useState, useEffect } from "react";
import { apiFetch, API_BASE } from "@/lib/api";

export interface TradePayload {
  action: "add" | "update" | "remove";
  symbol: string;
  name: string;
  market?: string;
  quantity: number;
  cost_price: number;
  account: string;
  accounts?: string[];
}

interface TradeConfirmCardProps {
  payload: TradePayload;
  onConfirm: (confirmed?: { account: string; quantity: number; cost_price: number }) => void;
  onCancel: () => void;
}

const ACTION_LABEL: Record<string, string> = {
  add: "买入",
  update: "更新",
  remove: "卖出",
};

export function TradeConfirmCard({ payload, onConfirm, onCancel }: TradeConfirmCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState(payload.account || "默认");
  const [costPrice, setCostPrice] = useState(String(payload.cost_price || ""));
  const [quantity, setQuantity] = useState(String(payload.quantity || ""));
  const [accounts, setAccounts] = useState<string[]>(payload.accounts || ["默认"]);

  useEffect(() => {
    if (payload.accounts?.length) {
      setAccounts(payload.accounts);
    } else {
      apiFetch(`${API_BASE}/api/portfolio/accounts`)
        .then((r) => r.json())
        .then((d) => {
          const names = (d.accounts || []).map((a: { name?: string; id?: string }) => a.name || a.id).filter(Boolean);
          setAccounts(names.length ? names : ["默认"]);
        })
        .catch(() => {});
    }
    setAccount(payload.account || "默认");
    setCostPrice(String(payload.cost_price || ""));
    setQuantity(String(payload.quantity || ""));
  }, [payload.account, payload.cost_price, payload.quantity, payload.accounts]);

  const handleConfirm = async () => {
    const qty = parseFloat(quantity) || 0;
    const price = parseFloat(costPrice) || 0;
    if (payload.action === "add" && (qty <= 0 || price <= 0)) {
      setError("请填写数量和成交均价");
      return;
    }
    if (payload.action === "update" && qty < 0) {
      setError("请填写数量");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/trade/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: payload.action,
          symbol: payload.symbol,
          name: payload.name,
          market: payload.market || "A",
          quantity: payload.action === "remove" ? 0 : qty,
          cost_price: payload.action === "remove" ? 0 : price,
          account: account || "默认",
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(data.detail || data.error || `请求失败 ${r.status}`);
      }
      onConfirm({ account, quantity: qty, cost_price: price });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-white/10 bg-white/5 p-4">
      <div className="space-y-3 text-sm">
        <div className="flex justify-between items-center">
          <span className="text-[#888888]">标的</span>
          <span className="text-white font-medium">
            {payload.name || payload.symbol} ({payload.symbol})
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-[#888888]">动作</span>
          <span className="text-[#00e701]">{ACTION_LABEL[payload.action] || payload.action}</span>
        </div>
        <div className="flex justify-between items-center gap-2">
          <span className="text-[#888888] shrink-0">账户</span>
          <select
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            className="flex-1 rounded border border-white/20 bg-black/50 px-2 py-1.5 text-white text-right focus:border-[#00e701]/50 focus:outline-none"
          >
            {accounts.map((a) => (
              <option key={a} value={a} className="bg-[#1a1a1a]">
                {a}
              </option>
            ))}
          </select>
        </div>
        {(payload.action === "add" || payload.action === "update") && (
          <>
            <div className="flex justify-between items-center gap-2">
              <span className="text-[#888888] shrink-0">数量</span>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="如 2000"
                className="flex-1 rounded border border-white/20 bg-black/50 px-2 py-1.5 text-white text-right placeholder:text-[#666] focus:border-[#00e701]/50 focus:outline-none"
              />
            </div>
            <div className="flex justify-between items-center gap-2">
              <span className="text-[#888888] shrink-0">成交均价</span>
              <input
                type="number"
                step="0.01"
                value={costPrice}
                onChange={(e) => setCostPrice(e.target.value)}
                placeholder="如 25.5"
                className="flex-1 rounded border border-white/20 bg-black/50 px-2 py-1.5 text-white text-right placeholder:text-[#666] focus:border-[#00e701]/50 focus:outline-none"
              />
            </div>
          </>
        )}
      </div>
      {error && (
        <div className="mt-2 text-xs text-red-400">{error}</div>
      )}
      <div className="mt-4 flex gap-2">
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="rounded-lg bg-[#00e701] px-4 py-2 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "写入中..." : "确认写入"}
        </button>
        <button
          onClick={onCancel}
          disabled={loading}
          className="rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-[#b1bad3] hover:bg-white/5 disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </div>
  );
}
