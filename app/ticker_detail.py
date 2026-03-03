"""个股深度 — 个股概览（Feed + 基本面）+ 个股分析（情绪）+ Ask PFA

UI 参考 NBot：圆点、字体、颜色、头部、Tab、Feed 列表、情绪卡片。
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import requests

from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from pfa.data.store import load_all_feed_items
from agents.secretary_agent import load_portfolio, fetch_single_symbol

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def _render_ticker_header(h: dict, current_price: float | None, pct: float | None, articles_count: int = 0):
    """个股页头部：面包屑、标的、涨跌徽章、情绪行（圆点+文案）。"""
    sym = h.get("symbol", "")
    name = h.get("name", sym)
    market = h.get("market", "?")
    full_name = f"{name} ({sym}.{market})"

    breadcrumb = f'<a href="/">Portfolio</a> / {escape(sym)}'
    price_html = ""
    if current_price is not None and pct is not None:
        badge_class = "up" if pct >= 0 else "down"
        sign = "+" if pct >= 0 else ""
        price_html = f'<span class="price-badge {badge_class}">{sign}{pct:.1f}% 今日</span>'

    # 情绪行：绿点 + 文案（暂无数据时显示「暂无情绪」）
    sentiment_label = "暂无情绪"
    if articles_count > 0:
        sentiment_label = f"近 72h · {articles_count} 条"
    sentiment_html = f'<span class="dot dot-bullish"></span>{escape(sentiment_label)}'

    updated = datetime.now(CST).strftime("%H:%M")
    meta_html = f'<span>Updated {updated}</span>'

    st.markdown(f"""
<div class="ticker-detail-header">
    <div class="ticker-breadcrumb">{breadcrumb}</div>
    <div class="ticker-name">{escape(sym)}</div>
    <div class="ticker-fullname">{escape(full_name)}</div>
    <div class="ticker-meta">
        {price_html}
        <span>{sentiment_html}</span>
        <span>{meta_html}</span>
    </div>
</div>""", unsafe_allow_html=True)


def _render_feed_list(items: list, name: str):
    """Feed 列表：每条左侧黄/橙圆点、标题、来源+时间、摘要、操作（深挖/保存/不相关）。"""
    if not items:
        st.markdown('<p class="pfa-body" style="color:#5F6368;">暂无新闻。点击「刷新数据」抓取。</p>', unsafe_allow_html=True)
        return
    st.markdown(f'<div class="pfa-title" style="margin-bottom:8px;">Feed</div><div class="feed-list">', unsafe_allow_html=True)
    for it in items[:15]:
        src_tag = it.source_id if it.source == "rss" else it.source
        meta = f"{src_tag} · {it.published_at[:16] if it.published_at else '—'}"
        snippet = (it.content_snippet[:120] + "…") if (it.content_snippet and len(it.content_snippet) > 120) else (it.content_snippet or "")
        st.markdown(f"""
<div class="feed-list-item">
    <span class="feed-dot"></span>
    <div class="feed-body">
        <div class="feed-title"><a href="{escape(it.url)}" target="_blank">{escape(it.title)}</a></div>
        <div class="feed-meta">{escape(meta)}</div>
        <div class="feed-snippet">{escape(snippet)}</div>
        <div class="feed-actions">
            <a href="{escape(it.url)}" target="_blank">深挖</a>
            <span>保存</span>
            <span>不相关</span>
        </div>
    </div>
</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_sentiment_tab_placeholder():
    """情绪 Tab 占位：Overall、7-Day、By Source、Alerts、Drivers 卡片。"""
    st.markdown("""
<div class="sentiment-score-card">
    <div class="pfa-caption" style="margin-bottom:8px;">Overall Sentiment</div>
    <div class="score-num bullish">—</div>
    <div class="pfa-body" style="color:#9AA0A6;margin-top:4px;">暂无情绪数据</div>
</div>
<div class="sentiment-score-card">
    <div class="pfa-caption" style="margin-bottom:8px;">7-Day Trend</div>
    <div class="pfa-body" style="color:#5F6368;">暂无</div>
</div>
<div class="sentiment-score-card">
    <div class="pfa-caption" style="margin-bottom:8px;">Sentiment by Source</div>
    <div class="pfa-body" style="color:#5F6368;">暂无</div>
</div>
<div class="sentiment-score-card">
    <div class="pfa-caption" style="margin-bottom:8px;">Sentiment Alerts</div>
    <div class="sentiment-alert"><span class="dot dot-neutral"></span>暂无预警</div>
</div>""", unsafe_allow_html=True)


def _render_ask_pfa_panel(h: dict, items: list):
    """右侧 Ask PFA 面板：仅针对当前标的的对话。"""
    sym = h.get("symbol", "")
    name = h.get("name", sym)
    market = h.get("market", "?")
    cost = h.get("cost_price")
    qty = h.get("quantity")

    st.markdown("""
<div class="expert-chat-panel">
    <div class="chat-panel-header">
        <span class="chat-panel-title">Ask PFA</span>
        <span class="chat-panel-badge">Live</span>
    </div>
    <div class="chat-panel-desc">基于 """ + escape(name) + """ 最新新闻，向 AI 提问</div>
    <div class="chat-panel-body">""", unsafe_allow_html=True)

    chat_key = f"ticker_chat_{sym}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    from app.theme_v2 import _logo_data_uri
    chat_box = st.container(height=320)
    with chat_box:
        for msg in st.session_state[chat_key]:
            role = msg["role"]
            avatar = _logo_data_uri() if role == "assistant" else None
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])

    # 自定义输入行：避免 st.chat_input 带来的白底
    ic1, ic2 = st.columns([4, 1])
    with ic1:
        ticker_input = st.text_input(
            f"关于 {name}，你想了解什么？",
            key=f"{chat_key}_input",
            label_visibility="collapsed",
            placeholder=f"例如：{name} 的未来 3 年增长逻辑？",
        )
    with ic2:
        ticker_send = st.button("发送", key=f"{chat_key}_send", type="primary")

    user_input = None
    if ticker_send and ticker_input.strip():
        user_input = ticker_input.strip()
        st.session_state[f"{chat_key}_input"] = ""

    st.markdown("</div></div>", unsafe_allow_html=True)

    if user_input:
        st.session_state[chat_key].append({"role": "user", "content": user_input})

        context = "\n".join(
            f"- [{it.published_at[:16] if it.published_at else ''}] {it.title}: {(it.content_snippet or '')[:120]}"
            for it in items[:10]
        )
        prompt = (
            f"你是一位跟踪 {name}({sym}.{market}) 的专业投研分析师。\n\n"
            f"最新新闻：\n{context or '暂无'}\n\n"
            f"持仓: 成本{cost}, 数量{qty}\n\n"
            f"问题: {user_input}\n\n"
            f"请基于新闻给出专业投资观点，中文回答，简洁有深度。"
        )
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if api_key:
            try:
                resp = requests.post(
                    DASHSCOPE_URL,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.4, "max_tokens": 1500},
                    timeout=60,
                )
                resp.raise_for_status()
                answer = resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                answer = f"分析失败: {e}"
        else:
            answer = "需要配置 DASHSCOPE_API_KEY"
        st.session_state[chat_key].append({"role": "assistant", "content": answer})
        st.rerun()


def render_ticker_detail_page(holding: dict, holdings: list, user: dict):
    """
    渲染个股深度整页（可由 pfa_dashboard 在 page=ticker&symbol= 时调用）。
    holding: 当前选中的持仓项；holdings: 全部持仓；user: 当前用户信息。
    """
    inject_v2_theme()
    render_topnav(active="portfolio", user_email=user.get("email") or ("已登录" if user.get("user_id") else ""))

    h = holding
    sym = h.get("symbol", "")
    name = h.get("name", sym)

    # 实时价与涨跌
    current_price = None
    pct = None
    try:
        from pfa.realtime_quote import get_realtime_quotes
        quotes = get_realtime_quotes([h])
        q = quotes.get(sym, {})
        if q.get("current"):
            current_price = float(q["current"])
            pct = float(q.get("percent", 0))
    except Exception:
        pass

    items = load_all_feed_items(symbol=sym, since_hours=72)
    articles_count = len(items)

    _render_ticker_header(h, current_price, pct, articles_count)

    # Tab：概览 | 情绪
    tab_overview, tab_sentiment = st.tabs(["概览", "情绪"])

    with tab_overview:
        col_info, col_feed, col_chat = st.columns([1, 1.5, 1.5])

        with col_info:
            st.markdown("### 基本面")
            if current_price is not None and pct is not None:
                pct_color = COLORS["positive"] if pct > 0 else COLORS["negative"] if pct < 0 else COLORS["neutral"]
                sign = "+" if pct > 0 else ""
                st.markdown(f"""
<div class="pfa-card">
    <div style="font-size:28px; font-weight:800;">{current_price}</div>
    <div style="font-size:16px; font-weight:600; color:{pct_color};">{sign}{pct}%</div>
</div>""", unsafe_allow_html=True)
            info_rows = [
                ("代码", sym), ("名称", name), ("市场", h.get("market", "?")),
                ("成本价", h.get("cost_price") or "—"), ("持仓量", h.get("quantity") or "—"),
                ("账户", h.get("account", "—")), ("来源", h.get("source", "—")),
            ]
            rows_html = "".join(
                f'<tr><td style="color:#5F6368;padding:3px 0;">{k}</td><td style="text-align:right;">{escape(str(v))}</td></tr>'
                for k, v in info_rows
            )
            st.markdown(f'<div class="pfa-card"><table style="width:100%;font-size:13px;">{rows_html}</table></div>', unsafe_allow_html=True)
            cost = h.get("cost_price")
            qty = h.get("quantity")
            if cost and qty and current_price:
                try:
                    c, q_num, cur = float(cost), float(qty), float(current_price)
                    pnl = (cur - c) * q_num
                    pnl_pct = ((cur - c) / c) * 100
                    pnl_color = COLORS["positive"] if pnl > 0 else COLORS["negative"]
                    st.markdown(f"""
<div class="pfa-card" style="border-left:4px solid {pnl_color};">
    <div style="font-size:12px; color:#5F6368;">持仓盈亏</div>
    <div style="font-size:22px; font-weight:700; color:{pnl_color};">{'+' if pnl > 0 else ''}{pnl:,.0f}</div>
    <div style="font-size:14px; color:{pnl_color};">{'+' if pnl_pct > 0 else ''}{pnl_pct:.2f}%</div>
</div>""", unsafe_allow_html=True)
                except (ValueError, TypeError):
                    pass

        with col_feed:
            st.markdown("### 新闻 Feed")
            if st.button("刷新数据", key="ticker_refresh", use_container_width=True):
                with st.spinner(f"Scout → {name}..."):
                    fetch_single_symbol(sym, name, h.get("market", "?"), 72)
                st.rerun()
            _render_feed_list(items, name)

        with col_chat:
            _render_ask_pfa_panel(h, items)

    with tab_sentiment:
        _render_sentiment_tab_placeholder()


# ---------------------------------------------------------------------------
# Standalone 入口：无 symbol 时用选择框选标的
# ---------------------------------------------------------------------------

def _run_standalone():
    """直接运行 streamlit run app/ticker_detail.py 时：v2 主题 + auth_v2 + 选标的后渲染."""
    from app.auth_v2 import get_user, render_login_page
    st.set_page_config(page_title="个股深度 | PFA", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    inject_v2_theme()
    user = get_user()
    if not user.get("user_id"):
        render_login_page()
        st.stop()
    render_topnav(active="portfolio", user_email=user.get("email") or ("已登录" if user.get("user_id") else ""))
    portfolio = load_portfolio()
    holdings = portfolio.get("holdings", [])
    if not holdings:
        st.warning("请先添加持仓。")
        st.stop()
    qsymbol = st.query_params.get("symbol", "").strip()
    if qsymbol:
        holding = next((x for x in holdings if str(x.get("symbol")) == qsymbol), None)
        if holding:
            render_ticker_detail_page(holding, holdings, user)
            return
    sym_map = {f"{h.get('name', h['symbol'])} ({h['symbol']}.{h.get('market', '?')})": h for h in holdings}
    selected = st.selectbox("选择标的", list(sym_map.keys()))
    render_ticker_detail_page(sym_map[selected], holdings, user)


if __name__ == "__main__" or not __name__.startswith("app."):
    _run_standalone()
