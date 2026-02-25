"""投研看板页 — 多 Agent 协作：Scout 抓取 → Analyst 分析 → Auditor 审核"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import run_full_pipeline, fetch_single_symbol

PORTFOLIO_PATH = ROOT / "config" / "my-portfolio.json"
CST = timezone(timedelta(hours=8))


def load_portfolio() -> dict:
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "holdings": []}


# --- Page ---
st.header("投研看板")

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

if not holdings:
    st.warning("暂无持仓。请先在「持仓管理」页添加标的。")
    st.stop()

# --- Sidebar controls ---
with st.sidebar:
    st.subheader("Agent 操作面板")
    hours = st.selectbox("时间窗口", [24, 48, 72, 168], index=2,
                         format_func=lambda h: f"{h} 小时")

    st.markdown("---")
    st.caption("**单标的抓取**")
    symbol_options = {f"{h['name']}({h['symbol']}.{h['market']})": h for h in holdings}
    selected_label = st.selectbox("选择标的", list(symbol_options.keys()))
    selected_h = symbol_options[selected_label]

    if st.button("Scout: 抓取该标的", use_container_width=True):
        with st.spinner(f"Scout 正在抓取 {selected_h['name']}..."):
            r = fetch_single_symbol(
                selected_h["symbol"], selected_h["name"],
                selected_h["market"], hours,
            )
        if r["status"] == "ok":
            st.success(f"Scout 完成：{r.get('count', 0)} 条新闻")
        else:
            st.error(f"Scout 失败：{r.get('error', '?')}")
        st.rerun()

    st.markdown("---")
    st.caption("**全流水线**")
    do_audit = st.checkbox("启用 Auditor 审核", value=True)
    if st.button("运行完整流水线", type="primary", use_container_width=True):
        placeholder = st.empty()
        with st.spinner("Scout → Analyst → Auditor ..."):
            result = run_full_pipeline(holdings, hours=hours, do_audit=do_audit)
        st.session_state["pipeline_result"] = result
        if result["status"] == "ok":
            st.success("全流水线完成")
        elif result["status"] == "partial":
            st.warning("部分完成")
        else:
            st.error(f"失败: {result.get('error', '?')}")
        st.rerun()

# --- Main layout ---
left, right = st.columns([1, 1])

# --- Left: holdings + news by symbol ---
with left:
    st.subheader("持仓 & 新闻")
    for h in holdings:
        sym = h.get("symbol", "?")
        name = h.get("name", sym)
        market = h.get("market", "?")
        with st.expander(f"**{name}** ({sym}.{market})", expanded=False):
            items = load_all_feed_items(symbol=sym, since_hours=hours)
            if items:
                for it in items[:15]:
                    st.markdown(
                        f"- [{it.title}]({it.url})  \n"
                        f"  <small style='color:gray'>{it.published_at} · {it.source}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption(f"近 {hours} 小时无相关新闻")

# --- Right: analysis + audit ---
with right:
    st.subheader("今日投研简报")

    pipeline = st.session_state.get("pipeline_result")

    if pipeline and pipeline.get("analyst_result"):
        ar = pipeline["analyst_result"]
        st.caption(f"Analyst ({ar.get('model', '?')}) · {ar.get('analysis_time', '')[:16]} · {ar.get('news_count_input', '?')} 条新闻")
        st.markdown(ar.get("analysis", ""))

        if pipeline.get("auditor_result"):
            audit = pipeline["auditor_result"]
            with st.expander(f"Auditor 审核意见 ({audit.get('backend', '?')})", expanded=True):
                st.markdown(audit.get("audit_result", ""))
    else:
        analyses = load_all_analyses()
        if analyses:
            latest = analyses[0]
            st.caption(f"{latest.model} · {latest.analysis_time[:16]}")
            st.markdown(latest.analysis)
        else:
            st.info("点击左侧「运行完整流水线」生成投研简报。")

# --- Pipeline log ---
if pipeline and pipeline.get("pipeline_log"):
    with st.expander("Agent 协作日志"):
        for line in pipeline["pipeline_log"]:
            st.text(line)
