"""执行分析 — 一键触发 Scout → Analyst → Auditor 全流水线"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_feed_items
from agents.secretary_agent import (
    load_portfolio, load_data_sources, run_full_pipeline, fetch_single_symbol,
)

st.header("执行分析")

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

if not holdings:
    st.warning("暂无持仓。请先在「持仓管理」页添加标的。")
    st.stop()

# --- Controls ---
col_a, col_b = st.columns(2)
hours = col_a.selectbox("时间窗口", [24, 48, 72, 168], index=2,
                        format_func=lambda h: f"{h} 小时")
do_audit = col_b.checkbox("启用 Auditor 审核", value=True)

st.markdown("---")

# --- Single symbol fetch ---
st.subheader("单标的抓取")
sym_map = {f"{h['name']}({h['symbol']}.{h.get('market','?')})": h for h in holdings}
sel = st.selectbox("选择标的", list(sym_map.keys()))
sel_h = sym_map[sel]

if st.button("Scout: 抓取该标的新闻"):
    with st.spinner(f"Scout 正在抓取 {sel_h['name']}..."):
        r = fetch_single_symbol(sel_h["symbol"], sel_h["name"],
                                sel_h.get("market", "?"), hours)
    if r["status"] == "ok":
        st.success(f"完成: {r.get('count', 0)} 条新闻")
        for it in r.get("items", [])[:8]:
            st.markdown(f"- [{it['title']}]({it['url']})  \n"
                        f"  <small style='color:gray'>{it['published_at']}</small>",
                        unsafe_allow_html=True)
    else:
        st.error(f"失败: {r.get('error', '?')}")

st.markdown("---")

# --- Full pipeline ---
st.subheader("全流水线分析")
st.caption("Scout 抓取全部持仓新闻 → Analyst 深度分析 → Auditor 交叉验证")

if st.button("运行完整流水线", type="primary", use_container_width=True):
    progress = st.empty()
    with st.spinner("执行中..."):
        result = run_full_pipeline(holdings, hours=hours, do_audit=do_audit)
    st.session_state["last_pipeline"] = result

    if result["status"] == "ok":
        st.success("全流水线完成")
    elif result["status"] == "partial":
        st.warning("部分完成（详见日志）")
    else:
        st.error(f"失败: {result.get('error', '?')}")

# --- Display results ---
pipe = st.session_state.get("last_pipeline")
if pipe:
    # Scout summary
    sr = pipe.get("scout_result") or {}
    if sr:
        by_sym = sr.get("by_symbol", {})
        summary = " · ".join(f"{k}: {v}条" for k, v in by_sym.items())
        st.metric("Scout 抓取", f"{sr.get('total', 0)} 条新闻", summary)

    # Analyst report
    ar = pipe.get("analyst_result") or {}
    if ar:
        st.subheader("Analyst 投研简报")
        st.caption(f"{ar.get('model','?')} · {ar.get('analysis_time','')[:16]} · "
                   f"{ar.get('news_count_input','?')} 条新闻输入")
        st.markdown(ar.get("analysis", ""))

    # Auditor review
    audit = pipe.get("auditor_result") or {}
    if audit:
        with st.expander(f"Auditor 审核意见 ({audit.get('backend','?')})", expanded=True):
            st.markdown(audit.get("audit_result", ""))

    # Pipeline log
    if pipe.get("pipeline_log"):
        with st.expander("Agent 协作日志"):
            for line in pipe["pipeline_log"]:
                st.text(line)
