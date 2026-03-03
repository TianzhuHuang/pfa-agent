"""
Chat API — AI 对话（支持 Streaming SSE）

复用 pfa/ai_chat.py。
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]  # 允许 type/payload 等扩展字段，仅使用 role/content
    user_id: Optional[str] = "admin"
    pending_trade: Optional[Dict] = None  # 多轮补全时携带上一轮解析结果


class ChatHistoryRequest(BaseModel):
    messages: List[Dict[str, Any]]
    user_id: Optional[str] = "admin"


class TickerChatRequest(BaseModel):
    symbol: str
    messages: List[Dict[str, Any]]
    session_id: Optional[str] = None


class TickerHistoryRequest(BaseModel):
    symbol: str
    session_id: Optional[str] = None
    messages: List[Dict[str, Any]]


@router.get("/chat/all-sessions")
def get_all_chat_sessions(user_id: str = "admin"):
    """首页用：返回全局对话 + 所有个股会话的合并列表，按 updated_at 倒序。"""
    from backend.services.chat_service import get_global_session_meta
    from backend.services.ticker_chat_service import list_all_ticker_sessions

    uid = user_id or "admin"
    out = []
    global_meta = get_global_session_meta(uid)
    if global_meta:
        out.append(global_meta)
    ticker_sessions = list_all_ticker_sessions(uid)
    out.extend(ticker_sessions)
    out.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"sessions": out[:60]}


@router.get("/chat/ticker-sessions")
def get_ticker_sessions(symbol: str = "", user_id: str = "admin"):
    """该标的的会话列表，每项含 session_id、first_question、updated_at。"""
    from backend.services.ticker_chat_service import list_sessions
    sym = (symbol or "").strip()
    if not sym:
        return {"sessions": []}
    sessions = list_sessions(user_id or "admin", sym)
    return {"sessions": sessions}


@router.get("/chat/ticker-history")
def get_ticker_history(symbol: str = "", session_id: str = "", user_id: str = "admin"):
    """加载指定会话消息。不传 session_id 时返回最后活跃会话的消息。"""
    from backend.services.ticker_chat_service import load_session, get_or_create_last_session
    sym = (symbol or "").strip()
    sid = (session_id or "").strip()
    uid = user_id or "admin"
    if not sym:
        return {"messages": []}
    if not sid:
        sid = get_or_create_last_session(uid, sym)
    if not sid:
        return {"messages": []}
    messages = load_session(uid, sym, sid)
    return {"messages": messages, "session_id": sid}


@router.post("/chat/ticker-history")
def save_ticker_history(req: TickerHistoryRequest):
    """保存个股会话。无 session_id 时新建并返回。"""
    from backend.services.ticker_chat_service import save_session, get_or_create_last_session
    import uuid
    sym = (req.symbol or "").strip()
    sid = (req.session_id or "").strip()
    messages = req.messages or []
    uid = "admin"
    if not sym:
        return {"ok": False, "error": "symbol required"}
    if not sid:
        sid = str(uuid.uuid4())
    save_session(uid, sym, sid, messages)
    return {"ok": True, "session_id": sid}


@router.post("/chat/stream-ticker")
def chat_stream_ticker(req: TickerChatRequest):
    """针对单标的的上下文对话，自动注入最新新闻作为背景知识。"""
    from pfa.ai_chat import call_ai_stream
    from pfa.data.store import load_all_feed_items
    from agents.secretary_agent import load_portfolio

    symbol = (req.symbol or "").strip()
    messages = req.messages or []
    if not symbol or not messages:
        return {"error": "symbol and messages required"}

    p = load_portfolio()
    holdings = p.get("holdings", [])
    holding = next((h for h in holdings if str(h.get("symbol", "")).strip() == symbol), None)
    name = holding.get("name", symbol) if holding else symbol
    market = holding.get("market", "A") if holding else "A"
    cost = holding.get("cost_price") or 0 if holding else 0
    qty = holding.get("quantity") or 0 if holding else 0

    items = load_all_feed_items(symbol=symbol, since_hours=72)
    context_lines = []
    for it in items[:10]:
        ts = (it.published_at or "")[:16]
        context_lines.append(f"- [{ts}] {it.title}: {(it.content_snippet or '')[:120]}")
    context = "\n".join(context_lines) if context_lines else "暂无"

    system = (
        f"你是一位跟踪 {name}({symbol}.{market}) 的专业投研分析师。\n\n"
        f"最新新闻：\n{context}\n\n"
        f"持仓: 成本 {cost}, 数量 {qty}\n\n"
        f"请基于新闻给出专业投资观点，中文回答，简洁有深度。"
    )
    full = [{"role": "system", "content": system}] + messages

    def generate():
        for chunk in call_ai_stream(full):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/history")
def get_chat_history(user_id: str = "admin"):
    """获取当前用户的对话历史。DB 优先，支持从 JSON 迁移。"""
    from backend.services.chat_store import load_chat_history, migrate_json_to_db
    uid = user_id or "admin"
    messages = load_chat_history(uid)
    if not messages:
        migrated = migrate_json_to_db(uid)
        if migrated:
            messages = load_chat_history(uid)
    return {"messages": messages}


@router.post("/chat/history")
def save_chat_history_endpoint(req: ChatHistoryRequest):
    """保存对话历史。DB 优先，保留换行符。"""
    from backend.services.chat_store import save_chat_history
    save_chat_history(req.messages, req.user_id or "admin")
    return {"status": "ok"}


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming AI 回复。返回 SSE。确认流：clarify/confirm，不直接执行。"""
    from pfa.ai_chat import (
        call_ai_stream,
        build_system_prompt,
        parse_trade_command,
        merge_trade_from_followup,
    )
    from agents.secretary_agent import load_portfolio
    from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices

    messages = req.messages
    if not messages:
        return {"error": "messages required"}

    def generate():
        try:
            yield from _generate_inner()
        except Exception as e:
            err_msg = str(e)[:200] if str(e) else "服务暂时不可用"
            yield f"data: {json.dumps({'type': 'chunk', 'content': f'抱歉，处理时出错：{err_msg}'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    def _generate_inner():
        last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        pending = req.pending_trade

        # 若有 pending，先合并补全信息
        if pending and last_user:
            parsed = merge_trade_from_followup(last_user, pending)
            parsed.setdefault("confidence", 80)
        else:
            parsed = parse_trade_command(last_user)

        if parsed and parsed.get("action") in ("add", "update", "remove") and parsed.get("confidence", 0) >= 60:
            # 直接展示可编辑确认卡，不再反问
            cost_price = float(parsed.get("price", 0) or 0)
            if cost_price <= 0:
                try:
                    from pfa.portfolio_valuation import get_realtime_prices
                    fake_holding = [{"symbol": parsed.get("symbol", ""), "market": parsed.get("market", "A")}]
                    prices = get_realtime_prices(fake_holding)
                    p = prices.get(parsed.get("symbol", ""), {})
                    if p.get("current"):
                        cost_price = float(p["current"])
                except Exception:
                    pass
            account = (str(parsed.get("account", "") or "").strip() or "默认")
            payload = {
                "action": parsed.get("action"),
                "symbol": parsed.get("symbol", ""),
                "name": parsed.get("name", ""),
                "market": parsed.get("market", "A"),
                "quantity": int(parsed.get("quantity", 0) or 0),
                "cost_price": cost_price,
                "account": account,
            }
            # 获取账户列表供前端下拉选择
            try:
                from agents.secretary_agent import get_accounts
                accs = get_accounts()
                payload["accounts"] = [a.get("name", a.get("id", "")) for a in (accs or []) if a.get("name") or a.get("id")]
                if "默认" not in payload["accounts"]:
                    payload["accounts"] = ["默认"] + payload["accounts"]
            except Exception:
                payload["accounts"] = ["默认"]
            yield f"data: {json.dumps({'type': 'confirm', 'message': '请填写或修改以下信息后点击「确认写入」。', 'payload': payload}, ensure_ascii=False)}\n\n"
            return

        # 非交易意图，走 AI 对话
        p = load_portfolio()
        holdings = p.get("holdings", [])
        val = {"total_value_cny": 0, "total_pnl_cny": 0, "total_pnl_pct": 0, "holding_count": 0, "account_count": 0, "by_account": {}}
        if holdings:
            fx = get_fx_rates()
            prices = get_realtime_prices(holdings)
            val = calculate_portfolio_value(holdings, prices, fx)
        system = build_system_prompt(holdings, val)
        full = [{"role": "system", "content": system}] + messages

        chunk_count = 0
        for chunk in call_ai_stream(full):
            chunk_count += 1
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        if chunk_count == 0:
            yield f"data: {json.dumps({'type': 'chunk', 'content': 'AI 暂无回复，请检查 DASHSCOPE_API_KEY 或稍后重试。'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
