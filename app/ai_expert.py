"""
AI Expert Chat Module — 持仓感知的投研专家对话

功能:
  - 自动注入持仓上下文 (system prompt)
  - 对话内调仓 (buy/sell/update + 确认卡片)
  - 个股深度分析 (symbol click → chat analysis)
  - 持仓风险分析 (AI 主动发起)
  - 晨报/预警消息嵌入
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.theme_v2 import COLORS

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

SYSTEM_PERSONA = """你是 PFA 投研专家，一位资深股票策略分析师。

你的特点：
- 专业且克制，不做过度承诺
- 基于数据和事实分析，不猜测
- 回答简洁有力，重点突出
- 了解 A 股、港股、美股市场
- 能识别用户的调仓指令并执行

用户当前持仓概况：
{portfolio_context}

回答规则：
- 使用中文
- 金额用 ¥ 符号 + 千分位
- 涨跌用 A 股惯例（红涨绿跌）
- 如果用户询问某只个股，结合持仓数据分析"""


def _build_system_prompt(holdings: List[Dict], val: Dict) -> str:
    """Build system prompt with portfolio context."""
    total_v = val.get("total_value_cny", 0)
    total_pnl = val.get("total_pnl_cny", 0)
    total_pct = val.get("total_pnl_pct", 0)
    sign = "+" if total_pnl >= 0 else ""

    top_holdings = []
    for acct_data in val.get("by_account", {}).values():
        for h in acct_data.get("holdings", []):
            top_holdings.append({
                "代码": h["symbol"],
                "名称": h.get("name", ""),
                "现价": h.get("current_price", ""),
                "成本": h.get("cost_price", ""),
                "数量": h.get("quantity", ""),
                "盈亏": f"{'+' if h['pnl_cny']>=0 else ''}{h['pnl_cny']:,.0f}",
                "涨跌": f"{'+' if h['pnl_pct']>=0 else ''}{h['pnl_pct']:.1f}%",
            })

    context = (
        f"总资产: ¥{total_v:,.0f}\n"
        f"总收益: {sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)\n"
        f"持仓数: {val.get('holding_count', 0)} 只, {val.get('account_count', 0)} 个账户\n\n"
        f"持仓明细:\n{json.dumps(top_holdings, ensure_ascii=False, indent=2)}"
    )

    return SYSTEM_PERSONA.format(portfolio_context=context)


def _call_ai(messages: List[Dict]) -> str:
    """Call Qwen API with conversation history."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return "需要配置 DASHSCOPE_API_KEY"
    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": messages,
                  "temperature": 0.4, "max_tokens": 1500},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI 服务暂不可用: {e}"


def _handle_trade_command(user_input: str, holdings: List[Dict]) -> Optional[str]:
    """Check if input is a trade command. Returns reply or None."""
    from pfa.ai_portfolio_assistant import parse_portfolio_command
    from agents.secretary_agent import load_portfolio, save_portfolio, add_memo

    parsed = parse_portfolio_command(user_input)
    if parsed.get("confidence", 0) < 60:
        return None

    action = parsed.get("action", "")
    sym = parsed.get("symbol", "")
    name = parsed.get("name", "")
    qty = parsed.get("quantity", 0)
    price = parsed.get("price", 0)
    now_str = datetime.now(CST).isoformat()
    p = load_portfolio()

    if action == "add":
        entry = {"symbol": sym, "name": name, "market": parsed.get("market", "A"),
                 "source": "ai_expert", "updated_at": now_str}
        if qty > 0: entry["quantity"] = qty
        if price > 0: entry["cost_price"] = price
        p.setdefault("holdings", []).append(entry)
        save_portfolio(p)
        return f"✅ 已买入 **{name}**({sym}) {qty}股" + (f" @{price}" if price else "")

    elif action == "update":
        for h in p.get("holdings", []):
            if h["symbol"] == sym:
                if qty >= 0: h["quantity"] = qty
                if price > 0: h["cost_price"] = price
                h["updated_at"] = now_str
                save_portfolio(p)
                return f"✅ 已更新 **{name}**({sym}) → 数量 {qty}" + (f" @{price}" if price else "")
        return f"⚠️ 未找到 {name}({sym})"

    elif action == "remove":
        before = len(p.get("holdings", []))
        p["holdings"] = [h for h in p.get("holdings", []) if h["symbol"] != sym]
        if len(p["holdings"]) < before:
            save_portfolio(p)
            return f"✅ 已删除 **{name}**({sym})"
        return f"⚠️ 未找到 {name}({sym})"

    elif action == "memo":
        ok = add_memo(sym, parsed.get("memo_action", "note"), parsed.get("text", user_input))
        return f"📝 已记录 **{name}**({sym}) 备忘" if ok else f"⚠️ 未找到 {name}({sym})"

    return None


def render_expert_chat(holdings: List[Dict], val: Dict):
    """Render the AI Expert chat panel."""
    # Init chat with context-aware welcome
    if "expert_chat" not in st.session_state:
        total_v = val.get("total_value_cny", 0)
        total_pnl = val.get("total_pnl_cny", 0)
        total_pct = val.get("total_pnl_pct", 0)
        sign = "+" if total_pnl >= 0 else ""

        welcome = (
            f"你好，我是你的投研专家。\n\n"
            f"你目前持有 **{val.get('holding_count', 0)}** 只标的，"
            f"总资产 **¥{total_v:,.0f}**，"
            f"今日收益 **{sign}¥{total_pnl:,.0f}** ({sign}{total_pct:.2f}%)。\n\n"
            f"你可以问我：\n"
            f"- 「分析一下我的持仓风险」\n"
            f"- 「加仓 500 股中海油 价格 24」\n"
            f"- 「茅台最近有什么消息」"
        )
        st.session_state["expert_chat"] = [{"role": "assistant", "content": welcome}]

    # Chat header
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="font-size:16px;font-weight:600;color:#E8EAED;">AI Expert</span>
    <span style="background:#43A047;color:#fff;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:600;">LIVE</span>
</div>
<div style="font-size:12px;color:#5F6368;margin-bottom:12px;">基于你的持仓，向 AI 投研专家提问</div>
""", unsafe_allow_html=True)

    # Chat container
    chat_box = st.container(height=420)
    with chat_box:
        for msg in st.session_state["expert_chat"]:
            avatar = "🤖" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # Input
    user_input = st.chat_input("和投研专家对话...")

    if user_input:
        st.session_state["expert_chat"].append({"role": "user", "content": user_input})

        # Try trade command first
        trade_reply = _handle_trade_command(user_input, holdings)

        if trade_reply:
            reply = trade_reply
        else:
            # General AI conversation with full context
            system_prompt = _build_system_prompt(holdings, val)
            messages = [{"role": "system", "content": system_prompt}]

            # Add recent conversation history (last 6 messages)
            for msg in st.session_state["expert_chat"][-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

            reply = _call_ai(messages)

        st.session_state["expert_chat"].append({"role": "assistant", "content": reply})
        st.rerun()


def inject_morning_greeting(val: Dict):
    """Inject morning greeting if first visit today."""
    today = datetime.now(CST).strftime("%Y-%m-%d")
    if st.session_state.get("last_greeting_date") == today:
        return

    total_pnl = val.get("total_pnl_cny", 0)
    sign = "+" if total_pnl >= 0 else ""

    greeting = (
        f"☀️ 早上好！昨日持仓{'盈利' if total_pnl >= 0 else '浮亏'} "
        f"**{sign}¥{total_pnl:,.0f}**。\n\n"
        f"是否需要我生成今日投研晨报？"
    )

    if "expert_chat" in st.session_state:
        st.session_state["expert_chat"].append({"role": "assistant", "content": greeting})

    st.session_state["last_greeting_date"] = today
