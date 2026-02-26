"""个股深度 — 基本面 + P&L + Feed 流 + Ask Agent"""

import json, os, sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import requests
from app.theme import inject_theme, theme_toggle, COLORS
from app.page_utils import page_init
from pfa.data.store import load_all_feed_items
from agents.secretary_agent import load_portfolio, fetch_single_symbol


user = page_init()

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
dark = st.session_state.get("dark_mode", True)

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.header("个股深度")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

sym_map = {f"{h['name']} ({h['symbol']}.{h.get('market','?')})": h for h in holdings}
selected = st.selectbox("选择标的", list(sym_map.keys()))
h = sym_map[selected]
sym, name, market = h["symbol"], h.get("name", h["symbol"]), h.get("market", "?")

if st.button("刷新数据", use_container_width=True):
    with st.spinner(f"Scout → {name}..."):
        fetch_single_symbol(sym, name, market, 72)
    st.rerun()

# ===================================================================
# Three-column layout
# ===================================================================
col_info, col_feed, col_chat = st.columns([1, 1.5, 1.5])

# --- LEFT: Fundamentals + P&L ---
with col_info:
    st.markdown("### 基本面")

    cost = h.get("cost_price")
    qty = h.get("quantity")
    acct = h.get("account", "—")
    src = h.get("source", "—")

    # Real-time quote (Sina API, instant)
    current_price = None
    try:
        from pfa.realtime_quote import get_realtime_quotes
        quotes = get_realtime_quotes([h])
        q = quotes.get(sym, {})
        if q.get("current"):
            current_price = q["current"]
            pct = q.get("percent", 0)
            pct_color = COLORS["positive"] if pct > 0 else COLORS["negative"] if pct < 0 else COLORS["neutral"]
            sign = "+" if pct > 0 else ""
            st.markdown(f"""
<div class="pfa-card">
    <div style="font-size:28px; font-weight:800;">{current_price}</div>
    <div style="font-size:16px; font-weight:600; color:{pct_color};">{sign}{pct}%</div>
</div>""", unsafe_allow_html=True)
    except Exception:
        pass

    info_rows = [("代码", sym), ("名称", name), ("市场", market),
                 ("成本价", cost or "—"), ("持仓量", qty or "—"),
                 ("账户", acct), ("来源", src)]

    info_html = '<div class="pfa-card"><table style="width:100%; font-size:13px;">'
    for k, v in info_rows:
        info_html += f'<tr><td style="color:{"#999" if dark else "#666"}; padding:3px 0;">{k}</td><td style="text-align:right;">{escape(str(v))}</td></tr>'
    info_html += '</table></div>'
    st.markdown(info_html, unsafe_allow_html=True)

    # P&L calculation
    if cost and qty and current_price:
        try:
            c, q_num, cur = float(cost), float(qty), float(current_price)
            pnl = (cur - c) * q_num
            pnl_pct = ((cur - c) / c) * 100
            pnl_color = COLORS["positive"] if pnl > 0 else COLORS["negative"]
            st.markdown(f"""
<div class="pfa-card" style="border-left:4px solid {pnl_color};">
    <div style="font-size:12px; color:{'#999' if dark else '#666'};">持仓盈亏</div>
    <div style="font-size:22px; font-weight:700; color:{pnl_color};">
        {'+'if pnl>0 else ''}{pnl:,.0f}
    </div>
    <div style="font-size:14px; color:{pnl_color};">
        {'+'if pnl_pct>0 else ''}{pnl_pct:.2f}%
    </div>
</div>""", unsafe_allow_html=True)
        except (ValueError, TypeError):
            pass

# --- MIDDLE: Feed ---
with col_feed:
    st.markdown("### 新闻 Feed")

    items = load_all_feed_items(symbol=sym, since_hours=72)
    if items:
        st.caption(f"近 72h · {len(items)} 条")
        for it in items[:15]:
            src_tag = it.source_id if it.source == "rss" else it.source
            st.markdown(f"""<div class="feed-item">
<div class="title"><a href="{escape(it.url)}" target="_blank">{escape(it.title)}</a></div>
<div class="snippet">{escape(it.content_snippet[:120] if it.content_snippet else '')}</div>
<div class="meta">{escape(it.published_at[:16] if it.published_at else '')} · {escape(src_tag)}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.info("暂无新闻。点击「刷新数据」抓取。")

# --- RIGHT: Ask Agent ---
with col_chat:
    st.markdown("### Ask PFA Agent")
    st.caption(f"基于 {name} 最新新闻，向 AI 提问")

    chat_key = f"chat_{sym}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    history = st.session_state[chat_key]

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(f"关于{name}，你想了解什么？")

    if user_input:
        history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        news_items = load_all_feed_items(symbol=sym, since_hours=72)
        context = "\n".join(
            f"- [{it.published_at[:16] if it.published_at else ''}] {it.title}: {it.content_snippet[:120]}"
            for it in news_items[:10]
        )

        prompt = (
            f"你是一位跟踪 {name}({sym}.{market}) 的专业投研分析师。\n\n"
            f"最新新闻：\n{context}\n\n"
            f"持仓: 成本{cost}, 数量{qty}\n\n"
            f"问题: {user_input}\n\n"
            f"请基于新闻给出专业投资观点，中文回答，简洁有深度。"
        )

        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if api_key:
            with st.chat_message("assistant"):
                with st.spinner("分析中..."):
                    try:
                        resp = requests.post(DASHSCOPE_URL,
                            headers={"Authorization": f"Bearer {api_key}",
                                     "Content-Type": "application/json"},
                            json={"model": "qwen-plus",
                                  "messages": [{"role": "user", "content": prompt}],
                                  "temperature": 0.4, "max_tokens": 1500},
                            timeout=60)
                        resp.raise_for_status()
                        answer = resp.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        answer = f"分析失败: {e}"
                st.markdown(answer)
            history.append({"role": "assistant", "content": answer})
        else:
            st.error("需要 DASHSCOPE_API_KEY")
