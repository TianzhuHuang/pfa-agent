"""分析中心 — 执行分析 + 历史存档（结构化渲染）"""

import json, sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.theme import inject_theme, theme_toggle, COLORS
from pfa.data.store import load_all_analyses
from agents.secretary_agent import load_portfolio, run_full_pipeline, fetch_single_symbol

inject_theme()
theme_toggle()

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])
dark = st.session_state.get("dark_mode", True)

st.header("分析中心")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

# ===================================================================
# Control console
# ===================================================================
st.subheader("分析控制台")
c1, c2, c3 = st.columns([2, 2, 1])
hours = c1.selectbox("时间窗口", [24, 48, 72, 168], index=2,
                     format_func=lambda h: f"{h} 小时")
do_audit = c2.checkbox("启用 Auditor", value=True)
sym_map = {f"{h['name']}({h['symbol']})": h for h in holdings}
sel_label = c3.selectbox("标的", list(sym_map.keys()), label_visibility="collapsed")

col_s, col_f = st.columns(2)
with col_s:
    if st.button("Scout: 抓取该标的", use_container_width=True):
        sel_h = sym_map[sel_label]
        with st.spinner(f"Scout → {sel_h['name']}..."):
            r = fetch_single_symbol(sel_h["symbol"], sel_h["name"],
                                    sel_h.get("market", "?"), hours)
        by_src = r.get("by_source", {})
        detail = " + ".join(f"{s}:{n}" for s, n in by_src.items()) if by_src else ""
        st.success(f"{r.get('count', 0)} 条 ({detail})") if r["status"] == "ok" else st.error(r.get("error"))

with col_f:
    if st.button("运行完整流水线", type="primary", use_container_width=True):
        with st.spinner("Scout → Analyst → Auditor ..."):
            result = run_full_pipeline(holdings, hours=hours, do_audit=do_audit)
        st.session_state["hub_pipeline"] = result
        st.success("完成") if result["status"] == "ok" else st.warning("部分完成")
        st.rerun()

# Display pipeline results
pipe = st.session_state.get("hub_pipeline")
if pipe and pipe.get("analyst_result"):
    _render_briefing_result(pipe) if False else None  # handled below
    ar = pipe["analyst_result"]
    briefing = ar.get("briefing")
    if not briefing:
        try:
            briefing = json.loads(ar.get("analysis", "{}"))
        except (json.JSONDecodeError, TypeError):
            briefing = None

    if briefing:
        _render_structured(briefing, dark)
    else:
        st.markdown(ar.get("analysis", ""))

    audit = pipe.get("auditor_result") or {}
    if audit:
        with st.expander(f"Auditor 审核 ({audit.get('backend', '?')})"):
            st.markdown(audit.get("audit_result", ""))

    if pipe.get("pipeline_log"):
        with st.expander("Agent 日志"):
            for line in pipe["pipeline_log"]:
                st.text(line)

# ===================================================================
# History archive with visual rendering
# ===================================================================
st.markdown("---")
st.subheader("历史存档")


def _render_structured(data, is_dark):
    """Render structured briefing JSON as visual cards."""
    ms = data.get("market_sentiment", {})
    score = ms.get("score", 50)
    label = ms.get("label", "Neutral")
    s_color = COLORS["bullish"] if label == "Bullish" else COLORS["bearish"] if label == "Bearish" else COLORS["neutral"]

    st.markdown(f"""
<div class="sentiment-banner">
    <div><div class="sentiment-label" style="color:{s_color};">● {escape(label)}</div>
    <div style="font-size:12px; color:#999;">{escape(ms.get('reason', ''))}</div></div>
    <div class="sentiment-score" style="color:{s_color};">{score}</div>
</div>""", unsafe_allow_html=True)

    for item in data.get("must_reads", [])[:5]:
        st.markdown(f"""<div class="pfa-card {item.get('priority', '')}">
    <div class="card-title">{escape(str(item.get('title', '')))} <span class="badge badge-{item.get('sentiment', 'neutral')}">{item.get('sentiment', '')}</span></div>
    <div class="card-body">{escape(str(item.get('summary', '')))}</div>
    <div class="card-meta">💼 {escape(str(item.get('impact_on_portfolio', '')))}</div>
</div>""", unsafe_allow_html=True)

    one = data.get("one_liner", "")
    if one:
        st.markdown(f"> {one}")


analyses = load_all_analyses()
if analyses:
    dates = sorted(set(a.analysis_time[:10] for a in analyses if a.analysis_time), reverse=True)
    sel_date = st.selectbox("日期", dates, index=0)
    filtered = [a for a in analyses if sel_date in a.analysis_time]
    st.caption(f"共 {len(filtered)} 条")

    for i, rec in enumerate(filtered):
        with st.expander(f"#{i+1}  {rec.analysis_time[:16]}  ·  {rec.model}  ·  {rec.news_count_input} 条",
                         expanded=(i == 0)):
            try:
                data = json.loads(rec.analysis)
                if isinstance(data, dict) and "market_sentiment" in data:
                    _render_structured(data, dark)
                else:
                    st.markdown(rec.analysis)
            except (json.JSONDecodeError, TypeError):
                st.markdown(rec.analysis)
            if rec.token_usage:
                st.caption(f"Token: {rec.token_usage.get('total_tokens', '?')}")
else:
    st.caption("暂无历史记录。")
