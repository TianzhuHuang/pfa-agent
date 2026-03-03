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
from app.notifications import inject_briefing_to_chat, add_notification
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import load_portfolio


inject_v2_theme()
user = get_user()
if not user.get('user_id'):
    st.warning('请先登录。')
    st.stop()
render_topnav(active='briefing', user_email=user.get('email') or ('已登录' if user.get('user_id') else ''))

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
    # Inject into AI chat and notification center
    if result.get("analyst_result"):
        b = result["analyst_result"].get("briefing")
        if not b:
            try:
                b = json.loads(result["analyst_result"].get("analysis", "{}"))
            except (json.JSONDecodeError, TypeError):
                b = None
        if b:
            inject_briefing_to_chat(b)
    st.rerun()

# --- Load briefing ---
briefing_data = None
raw = st.session_state.get("briefing")

if raw:
    # 优先使用本次流水线结果
    if raw.get("analyst_result"):
        briefing_data = raw["analyst_result"].get("briefing")
        if not briefing_data:
            try:
                briefing_data = json.loads(raw["analyst_result"].get("analysis", "{}"))
            except (json.JSONDecodeError, TypeError):
                pass
    # 若流水线未成功产生分析结果，向用户暴露错误信息（如未配置 DASHSCOPE_API_KEY）
    elif raw.get("status") != "ok":
        err_msg = raw.get("error") or "分析服务暂不可用，请检查 DASHSCOPE_API_KEY / OPENAI_API_KEY 配置。"
        st.error(f"晨报生成失败：{err_msg}")

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
        <div style="font-size:14px; color:{'#9AA0A6' if dark else '#5F6368'}; margin-top:4px;">{escape(reason)}</div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:12px; font-weight:500; color:{'#5F6368' if dark else '#9AA0A6'};">情绪指数</div>
        <div class="sentiment-score" style="color:{s_color};">{score}</div>
    </div>
</div>
<div class="score-track"><div class="score-fill" style="width:{score}%; background:{s_color};"></div></div>
""", unsafe_allow_html=True)

# ===================================================================
# Must-Reads (TradingView-style 观点卡片)
# ===================================================================
st.markdown('<div class="tv-section"><div class="tv-section-title">今日必读</div></div>', unsafe_allow_html=True)

for item in briefing_data.get("must_reads", [])[:5]:
    sentiment = item.get("sentiment", "neutral")
    title = escape(str(item.get("title", "")))
    summary = escape(str(item.get("summary", "")))
    impact = escape(str(item.get("impact_on_portfolio", "")))
    symbol = escape(str(item.get("related_symbol", "")))
    sym_raw = (item.get("related_symbol") or "").strip()
    sym_for_link = sym_raw.split(".")[0] if sym_raw else ""
    ticker_link = f'/?page=ticker&symbol={escape(sym_for_link)}' if sym_for_link else ""
    url = item.get("url", "")
    url_html = f' · <a href="{escape(url)}" target="_blank" style="color:#4285F4;">原文↗</a>' if url else ""
    pill_class = "long" if sentiment == "positive" else "short" if sentiment == "negative" else "neutral"
    pill_text = "看多" if sentiment == "positive" else "看空" if sentiment == "negative" else "中性"

    card_inner = f"""
<div class="tv-view-card">
    <div class="tv-card-header">
        <span class="tv-card-symbol">{symbol or "—"}</span>
        <span class="direction-pill {pill_class}">{pill_text}</span>
    </div>
    <div class="tv-card-title">{title}</div>
    <div class="tv-card-snippet">{summary}</div>
    <div class="tv-card-meta" style="color:#4285F4;">💼 {impact}</div>
    <div class="tv-card-meta">{symbol}{url_html}</div>
</div>"""
    if ticker_link:
        st.markdown(f'<a href="{ticker_link}" class="tv-view-card-link" style="text-decoration:none;color:inherit;display:block;">{card_inner}</a>', unsafe_allow_html=True)
    else:
        st.markdown(card_inner, unsafe_allow_html=True)

# ===================================================================
# Portfolio Moves (TradingView-style 标的 + 方向 + 摘要)
# ===================================================================
st.markdown('<div class="tv-section" style="margin-top:24px;"><div class="tv-section-title">持仓异动</div></div>', unsafe_allow_html=True)

moves = briefing_data.get("portfolio_moves", [])
if moves:
    grid_html = '<div class="move-grid">'
    for move in moves:
        s = move.get("sentiment", "neutral")
        pill_class = "long" if s == "positive" else "short" if s == "negative" else "neutral"
        pill_text = "看多" if s == "positive" else "看空" if s == "negative" else "中性"

        name = escape(str(move.get("name", "")))
        sym = escape(str(move.get("symbol", "")))
        sym_raw = (move.get("symbol") or "").strip()
        sym_for_link = sym_raw.split(".")[0] if sym_raw else sym_raw or ""
        ticker_link = f'/?page=ticker&symbol={escape(sym_for_link)}' if sym_for_link else ""
        evt = escape(str(move.get("event_summary", "")))
        hint = escape(str(move.get("action_hint", "")))

        card_inner = f"""
<div class="tv-view-card" style="border-left:3px solid {COLORS['positive'] if s == 'positive' else COLORS['negative'] if s == 'negative' else COLORS['neutral']};">
    <div class="tv-card-header">
        <span class="tv-card-symbol">{sym or name}</span>
        <span class="direction-pill {pill_class}">{pill_text}</span>
    </div>
    <div class="tv-card-title">{name}</div>
    <div class="tv-card-snippet">{evt}</div>
    <div class="tv-card-meta" style="color:#4285F4;">👉 {hint}</div>
</div>"""
        if ticker_link:
            grid_html += f'<a href="{ticker_link}" class="tv-view-card-link" style="text-decoration:none;color:inherit;display:block;">{card_inner}</a>'
        else:
            grid_html += card_inner
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
