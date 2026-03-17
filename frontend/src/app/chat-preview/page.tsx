"use client";

import React, { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  StatusBar,
  ChatHistorySidebar,
  HoldingsContextPanel,
  ImpactCard,
  ChatInputDock,
} from "@/components/chat-preview";
import type { ChatSessionItem } from "@/components/chat-preview";
import type { HoldingCardItem } from "@/components/chat-preview/HoldingCard";
import { ChatMessage } from "@/components/ChatMessage";
import { apiFetch, API_BASE } from "@/lib/api";
import { useDisplayCurrency } from "@/contexts/DisplayCurrencyContext";
import { LoadingOverlay } from "@/components/LoadingOverlay";

/** 牛熊/涨跌红绿 */
const COLOR_BEAR = "#c58b8b";
const COLOR_BULL = "#748e63";

/** API 返回的 session 项 */
interface ApiSession {
  type: "global" | "ticker";
  session_id: string;
  symbol?: string;
  symbol_name?: string;
  first_question: string;
  updated_at: string;
}

/** 消息（与首页/个股页一致，Phase 1 无 impactCard） */
interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  impactCard?: unknown;
  _debug?: {
    attachments?: {
      ocr?: { debug_timings?: Record<string, number> | null; client_ms?: number | null };
      links?: { debug_timings?: Record<string, number> | null; client_ms?: number | null; urls?: string[] };
    };
  };
}

function formatTimeAgo(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
  return d.toLocaleDateString("zh-CN");
}

/** 将 all-sessions 映射为侧栏所需格式；emotionTag 用 first_question 前 15 字占位 */
function mapSessionsToSidebar(apiSessions: ApiSession[]): ChatSessionItem[] {
  return apiSessions.map((s) => {
    const id = s.type === "global" ? "global" : `${s.symbol ?? ""}/${s.session_id}`;
    // NOTE: impact sentiment is not persisted yet; this is a lightweight heuristic until sessions store sentiment metadata.
    const sentiment: ChatSessionItem["sentiment"] =
      /利空|风险|警告|下跌|熊|偏空/.test(s.first_question || "")
        ? "negative"
        : /利好|机会|上涨|牛|偏多/.test(s.first_question || "")
          ? "positive"
          : "neutral";
    return {
      id,
      firstQuestion: s.first_question || (s.type === "global" ? "首页对话" : "个股对话"),
      emotionTag: (s.first_question || "").slice(0, 15) || "—",
      updatedAt: formatTimeAgo(s.updated_at),
      sentiment,
    };
  });
}

/** 从 portfolio API 的 by_account 拍平为 HoldingsContextPanel 所需列表 */
function portfolioToHoldingsList(val: {
  by_account?: Record<string, { holdings?: Array<Record<string, unknown>> }>;
}): HoldingCardItem[] {
  const list: HoldingCardItem[] = [];
  const byAccount = val?.by_account ?? {};
  for (const [acctName, acct] of Object.entries(byAccount)) {
    const holdings = acct?.holdings ?? [];
    for (const ho of holdings) {
      if (ho.is_cash) continue;
      const symbol = String(ho.symbol ?? "");
      if (!symbol) continue;
      const name = String(ho.name ?? symbol);
      const currency = ho.currency === "USD" ? "$" : ho.currency === "HKD" ? "HK$" : "¥";
      const rawExchange = ho.exchange;
      const market = (ho.market ?? "A").toString().toUpperCase().slice(0, 2);
      const exchange = rawExchange
        ? String(rawExchange)
        : market === "HK"
          ? "港股"
          : market === "US"
            ? "美股"
            : /^6/.test(symbol)
              ? "沪市"
              : /^0|^3/.test(symbol)
                ? "深市"
                : "A股";
      list.push({
        symbol,
        name,
        industry: "", // Phase 1 可先空，或后续从配置/API 扩展
        logo_url: ho.logo_url ?? undefined,
        exchange,
        position_pct: typeof ho.position_pct === "number" ? ho.position_pct : undefined,
        current_price: ho.current_price != null ? Number(ho.current_price) : null,
        today_pct: ho.today_pct != null ? Number(ho.today_pct) : null,
        currency,
        sentiment: undefined,
        _listKey: `${symbol}-${acctName || "default"}`,
      } as HoldingCardItem & { _listKey: string });
    }
  }
  return list;
}

function getHighlightedSymbols(messages: ChatMsg[]): string[] {
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.impactCard);
  if (!lastAssistant || !("impactCard" in lastAssistant) || !lastAssistant.impactCard) return [];
  const card = lastAssistant.impactCard as { impacts?: Array<{ symbol?: string }> };
  return (card.impacts ?? []).map((i) => i.symbol ?? "").filter(Boolean);
}

interface MockImpactCard {
  title: string;
  impacts: Array<{ symbol: string; name: string; level: string; levelLabel: string; sentiment?: string }>;
  summary: string;
}

function getImpactSentiment(impactCard: MockImpactCard): "positive" | "negative" | "neutral" {
  const neg = impactCard.impacts.filter((i) => i.sentiment === "negative").length;
  const pos = impactCard.impacts.filter((i) => i.sentiment === "positive").length;
  if (neg > pos) return "negative";
  if (pos > neg) return "positive";
  return "neutral";
}

export default function ChatPreviewPage() {
  const searchParams = useSearchParams();
  const { displayCurrency } = useDisplayCurrency();
  const [apiSessions, setApiSessions] = useState<ApiSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [portfolioVal, setPortfolioVal] = useState<Record<string, unknown> | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [attachmentSummary, setAttachmentSummary] = useState<string | null>(null);
  const [attachLoading, setAttachLoading] = useState(false);
  /** True while image upload + OCR is in flight; gates send button only, typing stays enabled */
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);
  const [lastOcrTiming, setLastOcrTiming] = useState<string | null>(null);
  const [lastLinkTiming, setLastLinkTiming] = useState<string | null>(null);
  const [attachmentStatus, setAttachmentStatus] = useState<
    { state: "idle" }
    | { state: "uploading"; kind: "image" | "link"; startedAt: number }
    | { state: "ready"; kind: "image" | "link"; summary: string }
    | { state: "failed"; kind: "image" | "link"; error: string }
  >({ state: "idle" });
  const [debugOpen, setDebugOpen] = useState(false);
  const debugEnabled = typeof window !== "undefined" && (window as unknown as { __PFA_DEBUG__?: boolean }).__PFA_DEBUG__;

  const sidebarSessions = mapSessionsToSidebar(apiSessions);
  const holdingsList = portfolioVal ? portfolioToHoldingsList(portfolioVal as { by_account?: Record<string, { holdings?: Array<Record<string, unknown>> }> }) : [];
  const hasHoldings = holdingsList.length > 0;
  const portfolioLoadFailed = !portfolioLoading && portfolioVal === null;
  const highlightedSymbols = getHighlightedSymbols(messages);

  // Minimal first-run onboarding: if portfolio empty, show a gentle hint once per browser.
  const [showOnboardingHint, setShowOnboardingHint] = useState(false);
  useEffect(() => {
    try {
      if (hasHoldings) return;
      const key = "pfa.chatPreview.onboardingShown";
      if (localStorage.getItem(key)) return;
      setShowOnboardingHint(true);
      localStorage.setItem(key, "1");
    } catch {
      // ignore
    }
  }, [hasHoldings]);

  /** 当前选中的会话：global 或 ticker(symbol, session_id) */
  const selectedSession = (() => {
    if (!activeSessionId) return null;
    if (activeSessionId === "global") return { type: "global" as const };
    const parts = activeSessionId.split("/");
    if (parts.length >= 2) return { type: "ticker" as const, symbol: parts[0], session_id: parts.slice(1).join("/") };
    return null;
  })();

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/chat/all-sessions`);
      const d = await r.json();
      const sessions = d.sessions ?? [];
      setApiSessions(sessions);
      setActiveSessionId((prev) => {
        if (prev) return prev;
        const session = searchParams.get("session");
        const symbol = searchParams.get("symbol");
        const sid = searchParams.get("session_id");
        if (session === "global") return "global";
        if (symbol && sid) return `${symbol}/${sid}`;
        if (sessions.length > 0) {
          const first = sessions[0];
          return first.type === "global" ? "global" : `${first.symbol ?? ""}/${first.session_id}`;
        }
        return null;
      });
    } catch {
      setApiSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, [searchParams]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const loadMessagesForSession = useCallback(
    async (session: { type: "global" } | { type: "ticker"; symbol: string; session_id: string }) => {
      setMessagesLoading(true);
      try {
        if (session.type === "global") {
          const r = await apiFetch(`${API_BASE}/api/chat/history`);
          const d = await r.json();
          const msgs = (d?.messages ?? []).map((m: { role?: string; content?: string }) => ({
            role: (m.role || "assistant") as "user" | "assistant",
            content: m.content ?? "",
          }));
          setMessages(msgs);
        } else {
          const r = await apiFetch(
            `${API_BASE}/api/chat/ticker-history?symbol=${encodeURIComponent(session.symbol)}&session_id=${encodeURIComponent(session.session_id)}`
          );
          const d = await r.json();
          const msgs = (d?.messages ?? []).map((m: { role?: string; content?: string }) => ({
            role: (m.role || "assistant") as "user" | "assistant",
            content: m.content ?? "",
          }));
          setMessages(msgs);
        }
      } catch {
        setMessages([]);
      } finally {
        setMessagesLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!selectedSession) {
      setMessages([]);
      return;
    }
    loadMessagesForSession(selectedSession);
  }, [activeSessionId]);

  const loadPortfolio = useCallback(async () => {
    setPortfolioLoading(true);
    try {
      const r = await apiFetch(`${API_BASE}/api/portfolio?display_currency=${displayCurrency}`);
      const d = await r.json();
      if (r.ok) setPortfolioVal(d);
      else setPortfolioVal(null);
    } catch {
      setPortfolioVal(null);
    } finally {
      setPortfolioLoading(false);
    }
  }, [displayCurrency]);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    setLeftOpen(false);
  }, []);

  const handleAttachImage = useCallback(async (file: File) => {
    setAttachLoading(true);
    setUploadingAttachment(true);
    setLastOcrTiming(null);
    setAttachmentSummary(null);
    setAttachmentStatus({ state: "uploading", kind: "image", startedAt: performance.now() });
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      const clientStart = performance.now();
      const r = await apiFetch(`${API_BASE}/api/portfolio/ocr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: dataUrl }),
      });
      const d = await r.json().catch(() => ({}));
      const clientElapsed = performance.now() - clientStart;
      if (r.ok && d.status === "ok") {
        const holdings = Array.isArray(d.holdings) ? d.holdings : [];
        const imageText = typeof (d as { image_text?: string }).image_text === "string" ? (d as { image_text: string }).image_text.trim() : "";
        if (holdings.length > 0) {
          const lines = (holdings as Array<{ symbol?: string; name?: string; quantity?: number; cost_price?: number }>).map(
            (h) => `${h.symbol ?? ""} ${h.name ?? ""} 数量 ${h.quantity ?? 0} 成本 ${h.cost_price ?? ""}`
          );
          setAttachmentSummary("以下为截图识别到的持仓，请据此分析：\n" + lines.join("\n"));
          setAttachmentStatus({ state: "ready", kind: "image", summary: "持仓截图识别完成" });
        } else if (imageText) {
          setAttachmentSummary("以下为截图内容，请据此分析：\n" + imageText);
          setAttachmentStatus({ state: "ready", kind: "image", summary: "截图文字提取完成" });
        } else {
          setAttachmentSummary("未识别到持仓或文字，请上传更清晰的持仓/新闻截图或换一张图再试。");
          setAttachmentStatus({ state: "failed", kind: "image", error: "未识别到持仓或文字" });
        }
        const debug = (d as { debug_timings?: { [k: string]: number } }).debug_timings;
        if (debug) {
          const totalMs = typeof debug.total_ms === "number" ? debug.total_ms : clientElapsed;
          const decodeMs = typeof debug.decode_ms === "number" ? debug.decode_ms : undefined;
          const holdingsMs = typeof debug.holdings_ocr_ms === "number" ? debug.holdings_ocr_ms : undefined;
          const textMs = typeof debug.text_ocr_ms === "number" ? debug.text_ocr_ms : undefined;
          const totalSec = (totalMs / 1000).toFixed(1);
          const parts: string[] = [];
          if (decodeMs != null) parts.push(`解码 ${Math.round(decodeMs)}ms`);
          if (holdingsMs != null) parts.push(`持仓OCR ${Math.round(holdingsMs)}ms`);
          if (textMs != null) parts.push(`文本OCR ${Math.round(textMs)}ms`);
          setLastOcrTiming(`上传+识别耗时约 ${totalSec}s（${parts.join("，")}）`);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            // Stash debug info on last assistant placeholder if present
            if (last && last.role === "assistant") {
              next[next.length - 1] = {
                ...last,
                _debug: {
                  ...(last._debug ?? {}),
                  attachments: {
                    ...(last._debug?.attachments ?? {}),
                    ocr: { debug_timings: debug, client_ms: clientElapsed },
                  },
                },
              };
            }
            return next;
          });
          // 控制台输出完整时序，便于调试
          // eslint-disable-next-line no-console
          console.log("OCR debug_timings", debug);
        } else {
          setLastOcrTiming(`上传+识别耗时约 ${(clientElapsed / 1000).toFixed(1)}s`);
        }
      } else {
        const err = (d as { error?: string }).error;
        setAttachmentSummary("截图识别失败：" + (err && String(err).trim() ? err : "未知错误"));
        setAttachmentStatus({ state: "failed", kind: "image", error: err ? String(err) : "未知错误" });
      }
    } catch (err) {
      setAttachmentSummary("上传失败：" + (err as Error).message);
      setAttachmentStatus({ state: "failed", kind: "image", error: (err as Error).message });
    } finally {
      setAttachLoading(false);
      setUploadingAttachment(false);
    }
  }, []);

  const handleSendMessage = useCallback(
    async (text: string) => {
      const raw = text.trim();
      if (!raw || streaming) return;
      const session = selectedSession ?? { type: "global" as const };
      if (session.type === "ticker" && !session.symbol) return;

      const t = attachmentSummary ? `${attachmentSummary}\n\n${raw}` : raw;
      setAttachmentSummary(null);

      const newUserMsg: ChatMsg = { role: "user", content: t };
      const prevMessages = [...messages, newUserMsg];
      setMessages([...prevMessages, { role: "assistant", content: "" }]);
      setStreaming(true);
      let assistantContent = "";

      const toSend = prevMessages.map((m) => ({ role: m.role, content: m.content || "" }));

      try {
        // 链接抓取在后台进行，不阻塞当前提问
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const urls: string[] = [];
        let m: RegExpExecArray | null;
        while ((m = urlRegex.exec(raw)) !== null) {
          urls.push(m[1]);
        }
        const uniqueUrls = Array.from(new Set(urls));
        if (uniqueUrls.length > 0) {
          setLinkLoading(true);
          setLastLinkTiming(null);
          setAttachmentStatus({ state: "uploading", kind: "link", startedAt: performance.now() });
          const linkStart = performance.now();
          (async () => {
            try {
              const resp = await apiFetch(`${API_BASE}/api/chat/fetch-links`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ urls: uniqueUrls }),
              });
              const data = await resp.json().catch(() => ({}));
              const clientMs = performance.now() - linkStart;
              const results = (data?.results ?? []) as Array<{
                url?: string;
                title?: string;
                text?: string;
                status?: string;
                error?: string;
              }>;
              const okItems = results.filter((r) => r.status === "ok" && (r.text || "").trim());
              if (okItems.length > 0) {
                const snippets = okItems.map((r) => {
                  const title = (r.title || "").trim();
                  const url = (r.url || "").trim();
                  const text = (r.text || "").trim().slice(0, 400);
                  const header = title || url;
                  return header ? `${header}\n${text}` : text;
                });
                setAttachmentSummary((prev) => {
                  const prefix = prev ? `${prev}\n\n` : "";
                  return `${prefix}以下为链接内容，请据此分析：\n${snippets.join("\n\n---\n\n")}`;
                });
              }
              const debug = (data as { debug_timings?: { [k: string]: number } }).debug_timings;
              if (debug) {
                const totalMs = typeof debug.total_ms === "number" ? debug.total_ms : clientMs;
                const totalSec = (totalMs / 1000).toFixed(1);
                setLastLinkTiming(`链接抓取耗时约 ${totalSec}s`);
                setAttachmentStatus({ state: "ready", kind: "link", summary: `已抓取 ${uniqueUrls.length} 条链接` });
                // eslint-disable-next-line no-console
                console.log("Link fetch debug_timings", debug);
              } else {
                setLastLinkTiming(`链接抓取耗时约 ${(clientMs / 1000).toFixed(1)}s`);
                setAttachmentStatus({ state: "ready", kind: "link", summary: `已抓取 ${uniqueUrls.length} 条链接` });
              }
            } catch (e) {
              // eslint-disable-next-line no-console
              console.error("fetch-links failed", e);
              setAttachmentStatus({ state: "failed", kind: "link", error: (e as Error).message });
            } finally {
              setLinkLoading(false);
            }
          })();
        }
        if (session.type === "global") {
          const r = await apiFetch(`${API_BASE}/api/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: toSend }),
          });
          if (!r.ok) throw new Error(`请求失败 ${r.status}`);
          const reader = r.body?.getReader();
          const decoder = new TextDecoder();
          if (reader) {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              const chunk = decoder.decode(value, { stream: true });
              for (const line of chunk.split("\n")) {
                if (line.startsWith("data: ")) {
                  try {
                    const d = JSON.parse(line.slice(6));
                    if (d.type === "chunk" && d.content) {
                      assistantContent += d.content;
                      setMessages((prev) => {
                        const next = [...prev];
                        const last = next[next.length - 1];
                        if (last?.role === "assistant") next[next.length - 1] = { ...last, content: assistantContent };
                        else next.push({ role: "assistant", content: assistantContent });
                        return next;
                      });
                    } else if (d.type === "impact" && d.payload) {
                      setMessages((prev) => {
                        const next = [...prev];
                        const last = next[next.length - 1];
                        if (last?.role === "assistant") next[next.length - 1] = { ...last, impactCard: d.payload };
                        return next;
                      });
                    } else if (d.type === "done") {
                      if (d.content) assistantContent = d.content;
                    }
                  } catch {
                    /* ignore */
                  }
                }
              }
            }
          }
          setStreaming(false);
          const finalMsg: ChatMsg = { role: "assistant", content: assistantContent || "暂无回复。" };
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") next[next.length - 1] = finalMsg;
            else next.push(finalMsg);
            return next;
          });
          const toSave = [...prevMessages, finalMsg];
          await apiFetch(`${API_BASE}/api/chat/history`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: toSave }),
          });
          loadSessions();
        } else {
          const sid = session.session_id || crypto.randomUUID();
          const r = await apiFetch(`${API_BASE}/api/chat/stream-ticker`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol: session.symbol, session_id: sid, messages: toSend }),
          });
          if (!r.ok) throw new Error(`请求失败 ${r.status}`);
          const reader = r.body?.getReader();
          const decoder = new TextDecoder();
          if (reader) {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              const chunk = decoder.decode(value, { stream: true });
              for (const line of chunk.split("\n")) {
                if (line.startsWith("data: ")) {
                  try {
                    const d = JSON.parse(line.slice(6));
                    if (d.type === "chunk" && d.content) {
                      assistantContent += d.content;
                      setMessages((prev) => {
                        const next = [...prev];
                        const last = next[next.length - 1];
                        if (last?.role === "assistant") next[next.length - 1] = { ...last, content: assistantContent };
                        else next.push({ role: "assistant", content: assistantContent });
                        return next;
                      });
                    } else if (d.type === "done") {
                      if (d.content) assistantContent = d.content;
                    }
                  } catch {
                    /* ignore */
                  }
                }
              }
            }
          }
          setStreaming(false);
          const finalMsg: ChatMsg = { role: "assistant", content: assistantContent || "暂无回复。" };
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") next[next.length - 1] = finalMsg;
            else next.push(finalMsg);
            return next;
          });
          const toSave = [...prevMessages, finalMsg];
          await apiFetch(`${API_BASE}/api/chat/ticker-history`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol: session.symbol, session_id: sid, messages: toSave }),
          });
          if (!activeSessionId?.startsWith(session.symbol)) {
            setActiveSessionId(`${session.symbol}/${sid}`);
          }
          loadSessions();
        }
      } catch (err) {
        const msg = (err as Error).message;
        setStreaming(false);
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") next[next.length - 1] = { role: "assistant", content: `错误: ${msg}` };
          else next.push({ role: "assistant", content: `错误: ${msg}` });
          return next;
        });
      }
    },
    [selectedSession, messages, streaming, activeSessionId, loadSessions, attachmentSummary]
  );

  const handleAttachClick = useCallback(
    (file: File) => {
      handleAttachImage(file);
    },
    [handleAttachImage]
  );

  if (portfolioLoading && !portfolioVal && !portfolioLoadFailed) {
    return <LoadingOverlay fullScreen text="加载中..." />;
  }

  if (portfolioLoadFailed) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] flex-col items-center justify-center bg-[#0A0F1E] px-4">
        <div className="mx-auto w-full max-w-md text-center">
          <h2 className="mb-2 text-lg font-semibold text-white">持仓加载失败</h2>
          <p className="mb-6 text-sm text-[#9AA0A6]">请刷新页面或检查网络后重试。</p>
          <button
            type="button"
            onClick={() => loadPortfolio()}
            className="rounded-xl border border-[#D4AF37]/40 bg-[#D4AF37]/10 px-6 py-3 text-sm font-medium text-[#D4AF37] hover:bg-[#D4AF37]/20"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  if (!portfolioLoading && portfolioVal != null && !hasHoldings) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] flex-col items-center justify-center bg-[#0A0F1E] px-4">
        <div className="mx-auto w-full max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <svg
              className="h-16 w-16 text-[#D4AF37]/70"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <h2 className="mb-2 text-lg font-semibold text-white">先录入持仓</h2>
          <p className="mb-8 text-sm text-[#9AA0A6]">
            上传截图或手动添加后，即可在此与 AI 基于持仓对话。
          </p>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-[#D4AF37]/40 bg-[#D4AF37]/10 px-6 py-4 text-sm font-medium text-[#D4AF37] transition-colors hover:bg-[#D4AF37]/20"
          >
            去首页录入
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col bg-[#0A0F1E]">
      <StatusBar lastUpdated={new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })} connected />

      <div className="flex flex-1 min-h-0">
        <aside
          className={`absolute left-0 top-0 z-40 h-full w-[240px] border-r border-white/5 bg-[#0A0F1E]/95 backdrop-blur-xl transition-transform lg:relative lg:z-auto lg:flex-shrink-0 lg:translate-x-0 ${
            leftOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <ChatHistorySidebar
            sessions={sidebarSessions}
            activeId={activeSessionId}
            onSelect={handleSelectSession}
          />
          {sessionsLoading && (
            <div className="p-2 text-center text-xs text-[#6B7280]">加载历史...</div>
          )}
        </aside>

        <div className="flex flex-1 flex-col min-w-0">
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-2 lg:hidden">
            <button
              type="button"
              onClick={() => setLeftOpen((o) => !o)}
              className="rounded p-2 text-[#9AA0A6] hover:bg-white/5 hover:text-white"
              aria-label="对话历史"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => setRightOpen((o) => !o)}
              className="ml-auto rounded p-2 text-[#9AA0A6] hover:bg-white/5 hover:text-white"
              aria-label="持仓"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {messagesLoading ? (
              <div className="flex min-h-[200px] items-center justify-center">
                <LoadingOverlay fullScreen={false} compact text="加载对话..." />
              </div>
            ) : (
              <div className="mx-auto max-w-2xl px-4 py-6">
                {showOnboardingHint && (
                  <div className="mb-4 rounded-xl border border-[#D4AF37]/20 bg-[#D4AF37]/5 p-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-[#D4AF37]">开始之前</div>
                    <p className="mt-1 text-xs leading-relaxed text-[#9AA0A6]">
                      先录入你的持仓（搜索 / 截图 / 文件），我才能回答“这件事与你何干”。
                    </p>
                  </div>
                )}
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="mb-4 flex justify-center">
                      <svg
                        className="h-12 w-12 text-[#D4AF37]/50"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden
                      >
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                      </svg>
                    </div>
                    <div className="rounded-lg border border-[#D4AF37]/20 bg-[#D4AF37]/5 p-4">
                      <p className="text-xs leading-relaxed text-[#9AA0A6]">
                        输入问题，我会基于你的持仓分析。
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {messages.map((m, i) => {
                      const hasImpact = m.role === "assistant" && m.impactCard;
                      const sentiment =
                        hasImpact && m.impactCard
                          ? getImpactSentiment(m.impactCard as MockImpactCard)
                          : null;
                      const borderColor =
                        sentiment === "negative" ? COLOR_BEAR : sentiment === "positive" ? COLOR_BULL : null;
                      return (
                        <div
                          key={i}
                          className={`space-y-3 ${borderColor ? "rounded-xl pl-3 -ml-1 border-l-4" : ""}`}
                          style={borderColor ? { borderLeftColor: borderColor } : undefined}
                        >
                          {hasImpact && borderColor && (
                            <div
                              className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider"
                              style={{ color: borderColor }}
                            >
                              {sentiment === "negative" && <>▼ 偏空 Bear</>}
                              {sentiment === "positive" && <>▲ 偏多 Bull</>}
                            </div>
                          )}
                          <ChatMessage
                            content={m.content}
                            role={m.role}
                            isStreaming={streaming && i === messages.length - 1 && m.role === "assistant"}
                          />
                          {hasImpact && m.impactCard && (
                            <div className="ml-8">
                              <ImpactCard
                                title={(m.impactCard as MockImpactCard).title}
                                impacts={(m.impactCard as MockImpactCard).impacts}
                                summary={(m.impactCard as MockImpactCard).summary}
                                deepDiveHref="/chat-preview/deep-dive"
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {(attachmentSummary || attachLoading || linkLoading) && (
            <div className="mx-auto max-w-2xl px-4 pb-2">
              <div className="flex items-start gap-2 rounded-lg border border-[#D4AF37]/30 bg-[#D4AF37]/5 px-3 py-2">
                {attachLoading || linkLoading ? (
                  <div className="flex flex-1 flex-col gap-1">
                    <span className="text-xs text-[#9AA0A6]">
                      {attachLoading ? "正在上传并识别图片…" : "正在抓取链接内容…"}
                    </span>
                    <div className="h-1 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full w-1/3 animate-[pulse_1.2s_ease-in-out_infinite] bg-[#D4AF37]" />
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="min-h-0 flex-1 min-w-0 flex flex-col">
                      <div className="text-xs text-[#D4AF37] max-h-[160px] overflow-y-auto whitespace-pre-wrap break-words pr-1">
                        {attachmentSummary}
                      </div>
                      {lastOcrTiming && (
                        <p className="mt-1 text-[10px] text-[#9AA0A6]">{lastOcrTiming}</p>
                      )}
                      {lastLinkTiming && (
                        <p className="mt-0.5 text-[10px] text-[#9AA0A6]">{lastLinkTiming}</p>
                      )}
                      <p className="mt-1 text-[10px] text-[#9AA0A6]">发送时将作为上下文一起提交</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setAttachmentSummary(null)}
                      className="shrink-0 text-[10px] text-[#9AA0A6] hover:text-white"
                    >
                      清除
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
          {debugEnabled && (
            <div className="mx-auto max-w-2xl px-4 pb-2">
              <button
                type="button"
                onClick={() => setDebugOpen((o) => !o)}
                className="text-[10px] text-[#9AA0A6] hover:text-white"
              >
                {debugOpen ? "收起调试信息" : "展开调试信息"}
              </button>
              {debugOpen && (
                <pre className="mt-2 max-h-[180px] overflow-y-auto rounded-lg border border-white/10 bg-black/20 p-3 text-[10px] leading-relaxed text-[#9AA0A6]">
{JSON.stringify({ attachmentStatus, lastOcrTiming, lastLinkTiming }, null, 2)}
                </pre>
              )}
            </div>
          )}
          <ChatInputDock
            onSend={handleSendMessage}
            onAttach={handleAttachClick}
            disabled={streaming || messagesLoading}
            sendDisabled={uploadingAttachment || linkLoading}
            showSamplePrompts={messages.length === 0}
          />
        </div>

        <aside
          className={`absolute right-0 top-0 z-40 h-full w-[300px] border-l border-white/5 bg-[#0A0F1E]/95 backdrop-blur-xl transition-transform lg:relative lg:z-auto lg:flex-shrink-0 lg:translate-x-0 ${
            rightOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <HoldingsContextPanel
            holdings={holdingsList}
            highlightedSymbols={highlightedSymbols}
            activeSummary={
              highlightedSymbols.length > 0 ? `本话关联：${highlightedSymbols.length} 只` : undefined
            }
          />
        </aside>
      </div>

      {(leftOpen || rightOpen) && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => {
            setLeftOpen(false);
            setRightOpen(false);
          }}
          aria-hidden
        />
      )}
    </div>
  );
}
