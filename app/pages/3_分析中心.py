"""分析中心 (Analysis Hub) — 执行分析 + 历史存档 合并"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import (
    load_portfolio, run_full_pipeline, fetch_single_symbol,
)

CST = timezone(timedelta(hours=8))
portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.header("分析中心")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

# ===================================================================
# Top: Analysis Console
# ===================================================================
st.subheader("分析控制台")

c1, c2, c3 = st.columns([2, 2, 1])
hours = c1.selectbox("时间窗口", [24, 48, 72, 168], index=2,
                     format_func=lambda h: f"{h} 小时")
do_audit = c2.checkbox("启用 Auditor 审核", value=True)

# Single stock
sym_map = {f"{h['name']}({h['symbol']}.{h.get('market','?')})": h for h in holdings}
sel_label = c3.selectbox("标的", list(sym_map.keys()), label_visibility="collapsed")

col_single, col_full = st.columns(2)

with col_single:
    if st.button("Scout: 抓取该标的", use_container_width=True):
        sel_h = sym_map[sel_label]
        with st.spinner(f"Scout → {sel_h['name']}..."):
            r = fetch_single_symbol(sel_h["symbol"], sel_h["name"],
                                    sel_h.get("market", "?"), hours)
        if r["status"] == "ok":
            by_src = r.get("by_source", {})
            detail = " + ".join(f"{s}:{n}" for s, n in by_src.items()) if by_src else ""
            st.success(f"{r.get('count', 0)} 条 ({detail})")
        else:
            st.error(r.get("error", "?"))

with col_full:
    if st.button("运行完整流水线", type="primary", use_container_width=True):
        with st.spinner("Scout → Analyst → Auditor ..."):
            result = run_full_pipeline(holdings, hours=hours, do_audit=do_audit)
        st.session_state["hub_pipeline"] = result
        if result["status"] == "ok":
            st.success("完成")
        elif result["status"] == "partial":
            st.warning("部分完成")
        else:
            st.error(result.get("error", "?"))
        st.rerun()

# Display pipeline results
pipe = st.session_state.get("hub_pipeline")
if pipe:
    ar = pipe.get("analyst_result") or {}
    audit = pipe.get("auditor_result") or {}
    sr = pipe.get("scout_result") or {}

    if sr:
        by_src = sr.get("by_source", {})
        src_text = " · ".join(f"{k}:{v}" for k, v in by_src.items())
        st.metric("Scout", f"{sr.get('total', 0)} 条", src_text)

    if ar:
        st.markdown("#### Analyst 投研报告")
        st.caption(f"{ar.get('model', '?')} · {ar.get('analysis_time', '')[:16]}")
        st.markdown(ar.get("analysis", ""))

    if audit:
        with st.expander(f"Auditor 审核 ({audit.get('backend', '?')})", expanded=False):
            st.markdown(audit.get("audit_result", ""))

    if pipe.get("pipeline_log"):
        with st.expander("Agent 日志"):
            for line in pipe["pipeline_log"]:
                st.text(line)

# ===================================================================
# Bottom: History Archive
# ===================================================================
st.markdown("---")
st.subheader("历史存档")

analyses = load_all_analyses()
if not analyses:
    st.caption("暂无历史分析记录。")
else:
    dates = sorted(set(a.analysis_time[:10] for a in analyses if a.analysis_time), reverse=True)
    sel_date = st.selectbox("日期", dates, index=0)
    filtered = [a for a in analyses if sel_date in a.analysis_time]
    st.caption(f"共 {len(filtered)} 条")

    for i, rec in enumerate(filtered):
        with st.expander(
            f"#{i+1}  {rec.analysis_time[:16]}  ·  {rec.model}  ·  {rec.news_count_input} 条新闻",
            expanded=(i == 0),
        ):
            st.markdown(rec.analysis)
            if rec.token_usage:
                st.caption(f"Token: {rec.token_usage.get('total_tokens', '?')}")
