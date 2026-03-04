"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

import { apiFetch, API_BASE } from "@/lib/api";
import { useColorScheme } from "@/contexts/ColorSchemeContext";

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

interface LogEntry {
  msg: string;
  color: "blue" | "purple" | "green" | "gray";
  ts: number;
  kind?: "status" | "ticker";
}

const STAGE_COLORS: Record<string, "blue" | "purple" | "green" | "gray"> = {
  scout_start: "blue",
  scout_done: "blue",
  analyst_start: "purple",
  analyst_heartbeat: "purple",
  analyst_done: "purple",
  analyst_fail: "purple",
  auditor_start: "purple",
  auditor_done: "purple",
  auditor_fail: "purple",
  auditor_skip: "gray",
  done: "green",
};

interface BriefingItem {
  title?: string;
  summary?: string;
  impact_on_portfolio?: string;
  url?: string;
}

interface Briefing {
  market_sentiment?: { score?: number; label?: string; reason?: string };
  must_reads?: BriefingItem[];
  one_liner?: string;
  portfolio_moves?: Array<{ symbol?: string; name?: string; event_summary?: string; action_hint?: string }>;
}

interface ReportRecord {
  id: number;
  date: string;
  summary?: string;
  content?: string;
  created_at?: string;
}

function BriefingContent({ briefing, onItemClick }: { briefing: Briefing; onItemClick: (item: BriefingItem) => void }) {
  const { upColor, downColor } = useColorScheme();
  const sentimentColor = (label?: string) => {
    if (label === "Bullish") return upColor;
    if (label === "Bearish") return downColor;
    return "text-[#888888]";
  };

  return (
    <div className="space-y-6">
      {briefing.market_sentiment && (
        <div className="rounded-lg bg-transparent py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className={`text-sm font-semibold ${sentimentColor(briefing.market_sentiment.label)}`}>
                ● {briefing.market_sentiment.label || "Neutral"}
              </div>
              <div className="prose prose-invert prose-sm max-w-none mt-2 text-[#b1bad3] leading-relaxed [&_p]:mb-4 [&_ul]:mb-4 [&_li]:mb-2">
                <ReactMarkdown>{briefing.market_sentiment.reason || ""}</ReactMarkdown>
              </div>
            </div>
            <div className={`text-2xl font-bold shrink-0 ${sentimentColor(briefing.market_sentiment.label)}`}>
              {briefing.market_sentiment.score ?? 50}
            </div>
          </div>
        </div>
      )}

      {briefing.one_liner && (
        <blockquote className="border-l-4 border-[#00e701] pl-4 text-sm text-[#b1bad3] italic leading-relaxed">
          {briefing.one_liner}
        </blockquote>
      )}

      {(briefing.portfolio_moves?.length ?? 0) > 0 && (
        <div className="space-y-4">
          <div className="text-xs font-medium uppercase tracking-wider text-[#888888]">异动标的</div>
          <ul className="space-y-4 leading-relaxed">
            {briefing.portfolio_moves!.map((m, i) => (
              <li key={i} className="rounded-lg bg-white/5 px-4 py-3">
                <div className="font-medium text-white">{m.name || m.symbol || "—"}</div>
                {m.event_summary && (
                  <div className="mt-1 text-sm text-[#b1bad3] leading-relaxed prose prose-invert prose-sm max-w-none [&_p]:mb-2">
                    <ReactMarkdown>{m.event_summary}</ReactMarkdown>
                  </div>
                )}
                {m.action_hint && <div className="mt-2 text-xs text-[#888]">💡 {m.action_hint}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(briefing.must_reads?.length ?? 0) > 0 && (
        <div className="space-y-0">
          <div className="mb-3 text-xs font-medium uppercase tracking-wider text-[#888888]">必读要点</div>
          <div className="divide-y divide-[#1a1a1a]">
            {briefing.must_reads!.map((item, i) => (
              <button
                key={i}
                onClick={() => onItemClick(item)}
                className="w-full py-4 text-left transition-colors hover:bg-white/[0.02]"
              >
                <div className="font-medium text-white">{item.title || "—"}</div>
                <div className="mt-1 line-clamp-2 text-sm text-[#888888] leading-relaxed prose prose-invert prose-sm max-w-none [&_p]:mb-1">
                  <ReactMarkdown>{item.summary || ""}</ReactMarkdown>
                </div>
                {item.impact_on_portfolio && (
                  <div className="mt-2 text-xs text-[#666]">💼 {item.impact_on_portfolio}</div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BriefingPage() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [logStream, setLogStream] = useState<LogEntry[]>([]);
  const [tickerStream, setTickerStream] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [drawerItem, setDrawerItem] = useState<BriefingItem | null>(null);
  const [history, setHistory] = useState<ReportRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [loadedContent, setLoadedContent] = useState<Record<number, Briefing>>({});
  const [loadError, setLoadError] = useState<Record<number, string>>({});
  const [filterYear, setFilterYear] = useState<string>("");
  const [filterMonth, setFilterMonth] = useState<string>("");
  const [filterDay, setFilterDay] = useState<string>("");
  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const tickerContainerRef = useRef<HTMLDivElement | null>(null);

  const today = todayStr();

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const params = new URLSearchParams({ limit: "30" });
      const y = filterYear || "";
      const m = filterMonth || "";
      const d = filterDay || "";
      if (y) {
        let fromDate: string;
        let toDate: string;
        if (y && m && d) {
          fromDate = toDate = `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
        } else if (y && m) {
          const lastDay = new Date(parseInt(y, 10), parseInt(m, 10), 0).getDate();
          fromDate = `${y}-${m.padStart(2, "0")}-01`;
          toDate = `${y}-${m.padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
        } else {
          fromDate = `${y}-01-01`;
          toDate = `${y}-12-31`;
        }
        params.set("from_date", fromDate);
        params.set("to_date", toDate);
      }
      const r = await apiFetch(`${API_BASE}/api/briefing/history?${params}`);
      const data = await r.json();
      const reports = data.reports ?? [];
      setHistory(reports);
      const todayReport = reports.find((x: ReportRecord) => x.date === today);
      if (todayReport) {
        setExpandedIds((prev) => new Set(prev).add(todayReport.id));
      }
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [filterYear, filterMonth, filterDay, today]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    logContainerRef.current?.scrollTo({ top: logContainerRef.current.scrollHeight, behavior: "smooth" });
  }, [logStream]);

  useEffect(() => {
    tickerContainerRef.current?.scrollTo({ top: tickerContainerRef.current.scrollHeight, behavior: "smooth" });
  }, [tickerStream]);

  const toggleExpand = useCallback((id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    expandedIds.forEach((id) => {
      if (!loadedContent[id] && !loadError[id]) {
        apiFetch(`${API_BASE}/api/briefing/${id}`)
          .then((r) => r.json())
          .then((d) => {
            if (d.status === "error") {
              setLoadError((prev) => ({ ...prev, [id]: d.error || "加载失败" }));
              return;
            }
            const content = typeof d.content === "string" ? JSON.parse(d.content) : d.content;
            if (content) setLoadedContent((prev) => ({ ...prev, [id]: content }));
            else setLoadError((prev) => ({ ...prev, [id]: "内容为空" }));
          })
          .catch((e) => {
            setLoadError((prev) => ({ ...prev, [id]: e.message || "网络错误" }));
          });
      }
    });
  }, [expandedIds, loadedContent, loadError]);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBriefing(null);
    setStatus(null);
    setLogStream([]);
    setTickerStream([]);
    try {
      const generateUrl = API_BASE.startsWith("http")
        ? `${API_BASE}/api/briefing/generate?hours=24`
        : `/api/briefing/generate?hours=24`;
      const r = await apiFetch(generateUrl, { method: "POST" });
      if (!r.ok) {
        const text = await r.text();
        setError(
          r.status === 502 || r.status === 503
            ? "后端服务未启动，请执行: uvicorn backend.main:app --port 8000"
            : `请求失败 (${r.status}): ${text.slice(0, 100)}`
        );
        return;
      }
      const reader = r.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        setError("无法读取响应流");
        return;
      }
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === "status") {
              const msg = evt.message || "";
              setStatus(msg);
              setLogStream((prev) => [
                ...prev,
                {
                  msg,
                  color: (evt.color as LogEntry["color"]) || STAGE_COLORS[evt.stage] || "gray",
                  ts: Date.now(),
                  kind: "status",
                },
              ]);
            } else if (evt.type === "ticker") {
              const msg = evt.message || "";
              const color = (evt.color as LogEntry["color"]) || "blue";
              setTickerStream((prev) => [...prev.slice(-99), { msg, color, ts: Date.now(), kind: "ticker" }]);
            } else if (evt.type === "done" && evt.result) {
              const res = evt.result;
              const ar = res?.analyst_result || {};
              let b: Briefing | null = ar.briefing;
              if (!b && ar.analysis) {
                try {
                  b = JSON.parse(ar.analysis);
                } catch {
                  b = null;
                }
              }
              setBriefing(b ?? null);
              setStatus("完成");
              setLogStream((prev) => [
                ...prev,
                { msg: "晨报已就绪", color: "green" as const, ts: Date.now(), kind: "status" },
              ]);
              if (!b && res?.error) setError(res.error);
              loadHistory();
            } else if (evt.type === "error") {
              setError(evt.error || "生成失败");
            }
          } catch {
            /* ignore */
          }
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
      setStatus(null);
    }
  }, [loadHistory]);

  const hasTodayReport = history.some((r) => r.date === today);

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-6 text-xl font-semibold text-white">投研晨报</h1>

      {/* 日期筛选：年/月/日 */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select
          value={filterYear}
          onChange={(e) => {
            setFilterYear(e.target.value);
            setFilterMonth("");
            setFilterDay("");
          }}
          className="rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white focus:border-[#1976d2]/50 focus:outline-none"
        >
          <option value="" className="bg-[#1a1a1a]">年</option>
          {Array.from({ length: 11 }, (_, i) => new Date().getFullYear() - 5 + i).map((y) => (
            <option key={y} value={String(y)} className="bg-[#1a1a1a]">{y}</option>
          ))}
        </select>
        <select
          value={filterMonth}
          onChange={(e) => {
            setFilterMonth(e.target.value);
            setFilterDay("");
          }}
          className="rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white focus:border-[#1976d2]/50 focus:outline-none"
        >
          <option value="" className="bg-[#1a1a1a]">月</option>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={String(m)} className="bg-[#1a1a1a]">{m} 月</option>
          ))}
        </select>
        <select
          value={filterDay}
          onChange={(e) => setFilterDay(e.target.value)}
          className="rounded border border-white/10 bg-black/50 px-3 py-2 text-sm text-white focus:border-[#1976d2]/50 focus:outline-none"
        >
          <option value="" className="bg-[#1a1a1a]">日</option>
          {Array.from(
            { length: filterYear && filterMonth ? new Date(parseInt(filterYear, 10), parseInt(filterMonth, 10), 0).getDate() : 31 },
            (_, i) => i + 1
          ).map((day) => (
            <option key={day} value={String(day)} className="bg-[#1a1a1a]">{day} 日</option>
          ))}
        </select>
        <button
          onClick={loadHistory}
          disabled={historyLoading || !filterYear}
          className="rounded border border-white/10 px-3 py-2 text-sm text-[#888] hover:bg-white/5 disabled:opacity-50"
        >
          {historyLoading ? "加载中..." : "筛选"}
        </button>
      </div>

      {/* 生成/更新今日晨报：始终显示，已有今日晨报时显示「更新晨报」 */}
      {!historyLoading && (
        <button
          onClick={generate}
          disabled={loading}
          className="mb-6 rounded-lg bg-[#00e701] px-5 py-2.5 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "生成中..." : hasTodayReport ? "更新晨报" : "生成今日晨报"}
        </button>
      )}

      {loading && (
        <div className="mb-6 space-y-4">
          <div className="rounded-lg border border-white/10 bg-black/50 p-4">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 animate-pulse rounded-full bg-[#00e701]" />
              <span className="text-sm font-medium text-white">{status || "准备中..."}</span>
            </div>
            {logStream.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#666]">
                {logStream
                  .filter((e) => e.kind === "status")
                  .slice(-5)
                  .map((e, i) => (
                    <span key={`${e.ts}-${i}`} className="truncate">
                      ✓ {e.msg}
                    </span>
                  ))}
              </div>
            )}
          </div>
          {tickerStream.length > 0 && (
            <div className="rounded-lg border border-white/10 bg-[#0a0a0a] p-3">
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[#666]">实时任务流</div>
              <div
                ref={tickerContainerRef}
                className="max-h-40 overflow-y-auto font-mono text-xs scroll-smooth"
              >
                {tickerStream.map((e, i) => (
                  <motion.div
                    key={`ticker-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2 }}
                    className={`flex items-center gap-2 py-0.5 ${
                      e.color === "blue"
                        ? "text-[#64b5f6]"
                        : e.color === "purple"
                          ? "text-[#b39ddb]"
                          : e.color === "green"
                            ? "text-[#00e701]"
                            : "text-[#888888]"
                    }`}
                  >
                    <span className="shrink-0 text-[#00e701]">●</span>
                    <span className="truncate">{e.msg}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-400">{error}</div>
      )}

      {/* 刚生成的晨报（生成完成后立即展示） */}
      {briefing && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 rounded-lg border border-gray-900/50 bg-black/30 p-6"
        >
          <div className="mb-4 text-sm font-medium text-[#888]">今日晨报 · {today}</div>
          <BriefingContent briefing={briefing} onItemClick={setDrawerItem} />
        </motion.div>
      )}

      {/* 历史晨报：按日期折叠 */}
      <div className="space-y-2">
        <div className="text-xs font-medium uppercase tracking-wider text-[#888888]">历史晨报</div>
        {historyLoading ? (
          <div className="py-8 text-center text-sm text-[#666]">加载中...</div>
        ) : history.length === 0 && !briefing ? (
          <div className="py-12 text-center">
            <div className="text-5xl opacity-20">📰</div>
            <p className="mt-4 text-sm text-[#666]">暂无晨报，点击上方按钮生成今日市场晨报</p>
          </div>
        ) : (
          history.map((r) => (
            <motion.div
              key={r.id}
              layout
              className="rounded-lg border border-gray-900/50 bg-black/30 overflow-hidden transition-shadow hover:shadow-lg"
            >
              <button
                onClick={() => toggleExpand(r.id)}
                className="flex w-full items-start justify-between gap-4 bg-black/50 px-4 py-3 text-left"
              >
                <span className="min-w-0 flex-1 font-medium text-white line-clamp-2">
                  {r.date} 投研晨报
                  {r.summary && (
                    <span className="ml-2 text-sm font-normal text-[#888]">| {r.summary}</span>
                  )}
                </span>
                <span className="shrink-0 text-[#888]">
                  {expandedIds.has(r.id) ? "▼" : "▶"}
                </span>
              </button>
              <AnimatePresence>
                {expandedIds.has(r.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="border-t border-white/5 px-4 pt-5 pb-4">
                      {loadedContent[r.id] ? (
                        <BriefingContent
                          briefing={loadedContent[r.id]}
                          onItemClick={setDrawerItem}
                        />
                      ) : loadError[r.id] ? (
                        <div className="py-4 text-center text-sm text-red-400">{loadError[r.id]}</div>
                      ) : (
                        <div className="py-4 text-center text-sm text-[#666]">加载中...</div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))
        )}
      </div>

      {/* 详情抽屉 */}
      {drawerItem && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40"
            onClick={() => setDrawerItem(null)}
            aria-hidden
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "tween", duration: 0.2 }}
            className="fixed right-0 top-12 z-50 h-[calc(100vh-48px)] w-full max-w-md border-l border-white/10 bg-black p-6 shadow-2xl overflow-y-auto"
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-lg font-semibold text-white">{drawerItem.title || "—"}</h3>
              <button
                onClick={() => setDrawerItem(null)}
                className="rounded p-1.5 text-[#888] hover:bg-white/10 hover:text-white"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mt-4 text-sm text-[#b1bad3] leading-relaxed prose prose-invert prose-sm max-w-none [&_p]:mb-3">
              <ReactMarkdown>{drawerItem.summary || ""}</ReactMarkdown>
            </div>
            {drawerItem.impact_on_portfolio && (
              <div className="mt-4 rounded-lg bg-white/5 px-4 py-2 text-xs text-[#888]">
                💼 {drawerItem.impact_on_portfolio}
              </div>
            )}
            {drawerItem.url && (
              <a
                href={drawerItem.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-block text-sm text-[#1976d2] hover:underline"
              >
                查看原文 →
              </a>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
