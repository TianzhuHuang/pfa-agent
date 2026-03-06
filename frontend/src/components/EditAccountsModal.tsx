"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { LoadingOverlay } from "@/components/LoadingOverlay";

const ACCOUNT_TYPES = ["股票", "债券", "数字货币", "其他"];

const CURRENCY_SYMBOLS: Record<string, string> = { CNY: "¥", USD: "$", HKD: "HK$" };

interface Account {
  id: string;
  name: string;
  base_currency: string;
  broker?: string;
  account_type?: string;
  balance?: number;
}

interface EditAccountsModalProps {
  open: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

export function EditAccountsModal({ open, onClose, onUpdated }: EditAccountsModalProps) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const r = await apiFetch(`${API_BASE}/api/portfolio/accounts`);
      const d = await r.json();
      const list = Array.isArray(d?.accounts) ? d.accounts : [];
      setAccounts(
        list.map((a: Record<string, unknown>) => ({
          id: String(a.id ?? a.name ?? ""),
          name: String(a.name ?? ""),
          base_currency: String(a.base_currency ?? a.currency ?? "CNY"),
          broker: String(a.broker ?? ""),
          account_type: String(a.account_type ?? "股票"),
          balance: Number(a.balance ?? 0),
        }))
      );
    } catch {
      setError("加载账户失败");
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) loadAccounts();
  }, [open, loadAccounts]);

  const updateLocal = (id: string, field: keyof Account, value: string | number) => {
    setAccounts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, [field]: value } : a))
    );
  };

  const handleSave = async (acc: Account) => {
    setSaving(acc.id);
    setError(null);
    try {
      const accountId = (acc.id || acc.name || "").trim();
      if (!accountId) {
        setError("账户 ID 为空");
        return;
      }
      const r = await apiFetch(`${API_BASE}/api/portfolio/accounts/${encodeURIComponent(accountId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: acc.name,
          broker: acc.broker ?? "",
          account_type: acc.account_type ?? "股票",
          balance: acc.balance ?? 0,
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(data.detail || data.error || `保存失败 (${r.status})`);
      }
      onUpdated?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async (acc: Account) => {
    const accountId = (acc.id || acc.name || "").trim();
    if (!accountId || accountId === "默认") {
      setError("「默认」账户不可删除");
      return;
    }
    if (!confirm(`确定删除账户「${acc.name}」？该账户下持仓将迁移至「默认」。`)) {
      return;
    }
    setDeleting(accountId);
    setError(null);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio/accounts/${encodeURIComponent(accountId)}`, {
        method: "DELETE",
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(data.detail || data.error || `删除失败 (${r.status})`);
      }
      setAccounts((prev) => prev.filter((a) => (a.id || a.name) !== accountId));
      onUpdated?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(null);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={onClose}
    >
      <div
        className="w-[95%] max-w-[560px] max-h-[90vh] overflow-y-auto rounded-xl bg-[#0a0a0a] p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">账户管理</h3>
          <button onClick={onClose} className="text-2xl text-[#888888] hover:text-white">
            ×
          </button>
        </div>
        <p className="mb-4 text-sm text-[#888888]">
          修改账户名称、账户类型。展示币种请在首页 Total Wealth 处切换。
        </p>
        {error && (
          <div className="mb-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-400">
            {error}
          </div>
        )}
        {loading ? (
          <LoadingOverlay fullScreen={false} text="稳扎稳打，数据正在搬运中..." />
        ) : accounts.length === 0 ? (
          <div className="py-8 text-center text-[#888888]">暂无账户，请先录入持仓</div>
        ) : (
          <div className="space-y-4">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="rounded-lg border border-white/10 bg-[#1a1a1a] p-4"
              >
                <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">账户名称</label>
                    <input
                      value={acc.name}
                      onChange={(e) => updateLocal(acc.id, "name", e.target.value)}
                      className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">账户类型</label>
                    <select
                      value={acc.account_type ?? "股票"}
                      onChange={(e) => updateLocal(acc.id, "account_type", e.target.value)}
                      className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                    >
                      {ACCOUNT_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">券商/托管方</label>
                    <input
                      value={acc.broker ?? ""}
                      onChange={(e) => updateLocal(acc.id, "broker", e.target.value)}
                      placeholder="可选"
                      className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-[#666]"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-[#888888]">可用余额</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min={0}
                        step={0.01}
                        value={acc.balance ?? 0}
                        onChange={(e) => updateLocal(acc.id, "balance", parseFloat(e.target.value) || 0)}
                        className="w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                      />
                      <span className="shrink-0 text-sm text-[#888888]">
                        {CURRENCY_SYMBOLS[acc.base_currency] ?? acc.base_currency}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleSave(acc)}
                    disabled={saving === acc.id}
                    className="rounded-lg bg-[#00e701] px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
                  >
                    {saving === acc.id ? "保存中..." : "保存"}
                  </button>
                  {(acc.id !== "默认" && acc.name !== "默认") && (
                    <button
                      onClick={() => handleDelete(acc)}
                      disabled={deleting === (acc.id || acc.name)}
                      className="rounded-lg border border-red-500/50 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                    >
                      {deleting === (acc.id || acc.name) ? "删除中..." : "删除"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
