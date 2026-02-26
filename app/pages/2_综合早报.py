"""
综合早报 (Morning Briefing)
ClawFeed 风格：AI 今日必读 + 持仓异动 + 卡片式展示
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import load_portfolio

CST = timezone(timedelta(hours=8))
now = datetime.now(CST)

# --- Card CSS ---
st.markdown("""<style>
.briefing-card {
    background: white; border-radius: 8px; padding: 16px;
    margin-bottom: 12px; border-left: 4px solid #1a73e8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.briefing-card.high { border-left-color: #ea4335; }
.briefing-card.medium { border-left-color: #fbbc04; }
.briefing-card.low { border-left-color: #34a853; }
.briefing-card .title { font-size: 15px; font-weight: 600; margin-bottom: 4px; color: #1a1a1a; }
.briefing-card .summary { font-size: 13px; color: #555; margin-bottom: 6px; }
.briefing-card .impact { font-size: 13px; color: #1a73e8; margin-bottom: 4px; }
.briefing-card .meta { font-size: 11px; color: #999; }
.sentiment-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 600; margin-left: 6px;
}
.sentiment-positive { background: #e6f4ea; color: #137333; }
.sentiment-negative { background: #fce8e6; color: #c5221f; }
.sentiment-neutral { background: #f1f3f4; color: #5f6368; }
.move-card {
    background: white; border-radius: 8px; padding: 14px;
    margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border-left: 4px solid #5f6368;
}
.move-card.positive { border-left-color: #34a853; }
.move-card.negative { border-left-color: #ea4335; }
.score-bar {
    height: 8px; border-radius: 4px; background: #f1f3f4;
    margin: 8px 0; position: relative; overflow: hidden;
}
.score-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
</style>""", unsafe_allow_html=True)

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.header(f"投研晨报 · {now.strftime('%m月%d日 %A')}")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

# --- Generate button ---
if st.button("生成今日晨报", type="primary", use_container_width=True):
    with st.spinner("Scout 抓取全源 → Analyst 结构化分析..."):
        from agents.secretary_agent import run_full_pipeline
        result = run_full_pipeline(holdings, hours=24, do_audit=False)
    st.session_state["briefing"] = result
    st.rerun()

# --- Load briefing data ---
briefing_data = None
raw_result = st.session_state.get("briefing")

if raw_result and raw_result.get("analyst_result"):
    briefing_data = raw_result["analyst_result"].get("briefing")
    if not briefing_data:
        try:
            briefing_data = json.loads(raw_result["analyst_result"].get("analysis", "{}"))
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
    st.info("点击上方「生成今日晨报」获取 AI 分析。")
    st.stop()

# ===================================================================
# Market Sentiment Banner
# ===================================================================
sentiment = briefing_data.get("market_sentiment", {})
score = sentiment.get("score", 50)
label = sentiment.get("label", "Neutral")
reason = sentiment.get("reason", "")

if label == "Bullish":
    color, emoji, bg = "#34a853", "📈", "#e6f4ea"
elif label == "Bearish":
    color, emoji, bg = "#ea4335", "📉", "#fce8e6"
else:
    color, emoji, bg = "#5f6368", "➡️", "#f1f3f4"

st.markdown(f"""
<div style="background:{bg}; border-radius:12px; padding:16px 24px; margin-bottom:20px; display:flex; align-items:center; justify-content:space-between;">
    <div>
        <span style="font-size:24px; font-weight:700; color:{color};">{emoji} {label}</span>
        <span style="font-size:14px; color:#666; margin-left:12px;">{reason}</span>
    </div>
    <div style="text-align:right;">
        <div style="font-size:11px; color:#999;">情绪指数</div>
        <div style="font-size:28px; font-weight:700; color:{color};">{score}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Score bar
fill_color = "#34a853" if score > 60 else "#ea4335" if score < 40 else "#fbbc04"
st.markdown(f"""
<div class="score-bar"><div class="score-fill" style="width:{score}%; background:{fill_color};"></div></div>
""", unsafe_allow_html=True)

# ===================================================================
# Must-Reads (Top 5)
# ===================================================================
st.subheader("今日必读")

must_reads = briefing_data.get("must_reads", [])
if must_reads:
    from html import escape as _esc
    for item in must_reads[:5]:
        priority = item.get("priority", "medium")
        sentiment_cls = item.get("sentiment", "neutral")
        badge_cls = f"sentiment-{sentiment_cls}"
        title = _esc(str(item.get('title', '')))
        summary = _esc(str(item.get('summary', '')))
        impact = _esc(str(item.get('impact_on_portfolio', '')))
        symbol = _esc(str(item.get('related_symbol', '')))
        url = item.get('url', '') or ''
        url_html = f'· <a href="{_esc(url)}" target="_blank">原文</a>' if url else ''

        st.markdown(f"""
<div class="briefing-card {_esc(priority)}">
    <div class="title">
        {title}
        <span class="sentiment-badge {badge_cls}">{_esc(sentiment_cls)}</span>
    </div>
    <div class="summary">{summary}</div>
    <div class="impact">💼 {impact}</div>
    <div class="meta">{symbol} {url_html}</div>
</div>
""", unsafe_allow_html=True)
else:
    st.caption("无必读条目")

# ===================================================================
# Portfolio Moves
# ===================================================================
st.markdown("---")
st.subheader("持仓异动")

moves = briefing_data.get("portfolio_moves", [])
if moves:
    from html import escape as _esc2
    cols = st.columns(min(len(moves), 3))
    for i, move in enumerate(moves):
        with cols[i % 3]:
            s = move.get("sentiment", "neutral")
            mname = _esc2(str(move.get('name', '')))
            msym = _esc2(str(move.get('symbol', '')))
            mevt = _esc2(str(move.get('event_summary', '')))
            mhint = _esc2(str(move.get('action_hint', '')))
            st.markdown(f"""
<div class="move-card {_esc2(s)}">
    <div style="font-size:15px; font-weight:600;">{mname} <span style="color:#999; font-size:12px;">{msym}</span></div>
    <div style="font-size:13px; color:#555; margin:6px 0;">{mevt}</div>
    <div style="font-size:12px; color:#1a73e8;">👉 {mhint}</div>
</div>
""", unsafe_allow_html=True)
else:
    st.caption("无持仓异动数据")

# ===================================================================
# One-liner
# ===================================================================
one_liner = briefing_data.get("one_liner", "")
if one_liner:
    st.markdown("---")
    st.markdown(f"> **总结**: {one_liner}")

# ===================================================================
# Raw news feed (collapsed)
# ===================================================================
with st.expander("完整新闻流", expanded=False):
    all_items = load_all_feed_items(since_hours=24)
    if all_items:
        st.caption(f"近 24h 共 {len(all_items)} 条")
        for it in all_items[:20]:
            src = it.source_id if it.source == "rss" else it.source
            sym_tag = f" · {it.symbol_name}" if it.symbol_name else ""
            st.markdown(
                f"- [{it.title}]({it.url})  \n"
                f"  <small style='color:gray'>{it.published_at[:16] if it.published_at else ''} · {src}{sym_tag}</small>",
                unsafe_allow_html=True,
            )
