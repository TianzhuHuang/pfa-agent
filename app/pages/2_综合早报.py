"""综合早报 — AI 今日必读 + 持仓异动 (A股色系: 红涨绿跌)"""

import json, sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import load_portfolio


inject_v2_theme()
user = get_user()
if not user.get('user_id'):
    st.warning('请先登录。')
    st.stop()
render_topnav(active='briefing', user_email=user.get('email', ''))

CST = timezone(timedelta(hours=8))
now = datetime.now(CST)

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.header(f"投研晨报 · {now.strftime('%m月%d日 %A')}")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

if st.button("生成今日晨报", type="primary", use_container_width=True):
    with st.spinner("Scout 全源抓取 → Analyst 结构化分析..."):
        from agents.secretary_agent import run_full_pipeline
        result = run_full_pipeline(holdings, hours=24, do_audit=False)
    st.session_state["briefing"] = result
    st.rerun()

# --- Load briefing ---
briefing_data = None
raw = st.session_state.get("briefing")
if raw and raw.get("analyst_result"):
    briefing_data = raw["analyst_result"].get("briefing")
    if not briefing_data:
        try:
            briefing_data = json.loads(raw["analyst_result"].get("analysis", "{}"))
        except (json.JSONDecodeError, TypeError):
            pass
if not briefing_data:
    analyses = load_all_analyses()
    if analyses:
        try:
            briefing_data = json.loads(analyses[0].analysis)
        except (json.JSONDecodeError, TypeError):
            pass
if not briefing_data:
    st.info("点击上方按钮生成晨报。")
    st.stop()

# ===================================================================
# Sentiment Banner
# ===================================================================
ms = briefing_data.get("market_sentiment", {})
score = ms.get("score", 50)
label = ms.get("label", "Neutral")
reason = ms.get("reason", "")

if label == "Bullish":
    s_color = COLORS["bullish"]  # 红 = 看多 (A股)
elif label == "Bearish":
    s_color = COLORS["bearish"]  # 绿 = 看空
else:
    s_color = COLORS["neutral"]

dark = st.session_state.get("dark_mode", True)
card_bg = COLORS["bg_card_dark"] if dark else COLORS["bg_card_light"]
border = COLORS["border_dark"] if dark else COLORS["border_light"]

st.markdown(f"""
<div class="sentiment-banner">
    <div>
        <div class="sentiment-label" style="color:{s_color};">● {label}</div>
        <div style="font-size:13px; color:{'#999' if dark else '#666'}; margin-top:4px;">{escape(reason)}</div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:11px; color:{'#666' if dark else '#999'};">情绪指数</div>
        <div class="sentiment-score" style="color:{s_color};">{score}</div>
    </div>
</div>
<div class="score-track"><div class="score-fill" style="width:{score}%; background:{s_color};"></div></div>
""", unsafe_allow_html=True)

# ===================================================================
# Must-Reads
# ===================================================================
st.subheader("今日必读")

for item in briefing_data.get("must_reads", [])[:5]:
    priority = item.get("priority", "medium")
    sentiment = item.get("sentiment", "neutral")
    title = escape(str(item.get("title", "")))
    summary = escape(str(item.get("summary", "")))
    impact = escape(str(item.get("impact_on_portfolio", "")))
    symbol = escape(str(item.get("related_symbol", "")))
    url = item.get("url", "")
    url_html = f' · <a href="{escape(url)}" target="_blank" style="color:{COLORS["accent"] if dark else COLORS["bullish"]};">原文↗</a>' if url else ""

    st.markdown(f"""
<div class="pfa-card {priority}">
    <div class="card-title">{title} <span class="badge badge-{sentiment}">{sentiment}</span></div>
    <div class="card-body">{summary}</div>
    <div class="card-body" style="color:{COLORS['accent'] if dark else COLORS['bullish']};">💼 {impact}</div>
    <div class="card-meta">{symbol}{url_html}</div>
</div>""", unsafe_allow_html=True)

# ===================================================================
# Portfolio Moves (A-share: red=up, green=down)
# ===================================================================
st.markdown("---")
st.subheader("持仓异动")

moves = briefing_data.get("portfolio_moves", [])
if moves:
    grid_html = '<div class="move-grid">'
    for move in moves:
        s = move.get("sentiment", "neutral")
        if s == "positive":
            border_color = COLORS["positive"]  # 红
        elif s == "negative":
            border_color = COLORS["negative"]  # 绿
        else:
            border_color = COLORS["neutral"]

        name = escape(str(move.get("name", "")))
        sym = escape(str(move.get("symbol", "")))
        evt = escape(str(move.get("event_summary", "")))
        hint = escape(str(move.get("action_hint", "")))

        grid_html += f"""
<div class="pfa-card" style="border-left:4px solid {border_color};">
    <div class="card-title">{name} <span style="color:{'#666' if dark else '#999'}; font-size:12px;">{sym}</span></div>
    <div class="card-body">{evt}</div>
    <div class="card-meta" style="color:{COLORS['accent'] if dark else COLORS['bullish']};">👉 {hint}</div>
</div>"""
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

# ===================================================================
# One-liner
# ===================================================================
one_liner = briefing_data.get("one_liner", "")
if one_liner:
    st.markdown("---")
    st.markdown(f"> **总结**: {one_liner}")

# ===================================================================
# Full feed (collapsed)
# ===================================================================
with st.expander("完整新闻流"):
    items = load_all_feed_items(since_hours=24)
    if items:
        st.caption(f"近 24h 共 {len(items)} 条")
        for it in items[:20]:
            src = it.source_id if it.source == "rss" else it.source
            sym_tag = f" · {it.symbol_name}" if it.symbol_name else ""
            st.markdown(f"""<div class="feed-item">
<div class="title"><a href="{escape(it.url)}" target="_blank">{escape(it.title)}</a></div>
<div class="meta">{escape(it.published_at[:16] if it.published_at else '')} · {escape(src)}{sym_tag}</div>
</div>""", unsafe_allow_html=True)
