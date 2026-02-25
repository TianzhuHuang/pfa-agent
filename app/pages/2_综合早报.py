"""综合早报 (Morning Briefing) — 每日市场情绪 + 持仓关键事件 + AI 摘要"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import requests
from pfa.data.store import load_all_feed_items, load_all_analyses
from agents.secretary_agent import load_portfolio
from pfa.stock_search import search_stock

PORTFOLIO_PATH = ROOT / "config" / "my-portfolio.json"
CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])
now = datetime.now(CST)

st.header(f"综合早报 · {now.strftime('%Y-%m-%d %A')}")

if not holdings:
    st.warning("请先在「持仓管理」页添加持仓。")
    st.stop()

# --- Generate briefing button ---
if st.button("生成今日早报", type="primary", use_container_width=True):
    with st.spinner("Scout 抓取 + Analyst 分析中..."):
        from agents.secretary_agent import run_full_pipeline
        result = run_full_pipeline(holdings, hours=24, do_audit=False)
    st.session_state["briefing_result"] = result
    st.rerun()

briefing = st.session_state.get("briefing_result")

# --- Layout: left=macro, right=holdings ---
col_macro, col_holdings = st.columns([1, 1])

# === Left: Macro sentiment ===
with col_macro:
    st.subheader("市场脉搏")

    # Fetch macro headlines from wallstreetcn
    macro_items = load_all_feed_items(source="wallstreetcn", since_hours=24)
    rss_items = load_all_feed_items(source="rss", since_hours=24)

    if macro_items or rss_items:
        # Show sentiment from latest analysis
        if briefing and briefing.get("analyst_result"):
            analysis = briefing["analyst_result"].get("analysis", "")
            if "利好" in analysis or "偏暖" in analysis or "积极" in analysis:
                st.success("**市场情绪: Bullish** 📈")
            elif "利空" in analysis or "偏冷" in analysis or "风险" in analysis:
                st.error("**市场情绪: Bearish** 📉")
            else:
                st.info("**市场情绪: Neutral** ➡️")
        else:
            latest_analyses = load_all_analyses()
            if latest_analyses:
                a = latest_analyses[0].analysis
                if "利好" in a or "偏暖" in a or "积极" in a:
                    st.success("**市场情绪: Bullish** 📈")
                elif "利空" in a or "偏冷" in a or "风险" in a:
                    st.error("**市场情绪: Bearish** 📉")
                else:
                    st.info("**市场情绪: Neutral** ➡️")

        st.markdown("**宏观快讯**")
        display_items = (macro_items or [])[:5]
        for it in display_items:
            st.markdown(
                f"- [{it.title}]({it.url})  \n"
                f"  <small style='color:gray'>{it.published_at[:16] if it.published_at else ''}</small>",
                unsafe_allow_html=True,
            )

        # RSS highlights
        rss_relevant = [it for it in rss_items if it.source_id in ("财联社-电报", "格隆汇-快讯", "金十快讯")][:5]
        if rss_relevant:
            st.markdown("**金融快讯**")
            for it in rss_relevant:
                st.markdown(
                    f"- [{it.title}]({it.url})  \n"
                    f"  <small style='color:gray'>{it.source_id} · {it.published_at[:16] if it.published_at else ''}</small>",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("暂无宏观数据。点击上方「生成今日早报」抓取最新信息。")

# === Right: Holdings overview ===
with col_holdings:
    st.subheader("持仓概览")

    for h in holdings:
        sym = h.get("symbol", "?")
        name = h.get("name", sym)
        market = h.get("market", "?")
        account = h.get("account", "")
        acct_tag = f" · {account}" if account and account != "默认" else ""

        items = load_all_feed_items(symbol=sym, since_hours=24)
        count = len(items)
        indicator = f"🔴 {count}条" if count > 5 else f"🟡 {count}条" if count > 0 else "⚪ 0条"

        with st.expander(f"**{name}** ({sym}.{market}){acct_tag}  {indicator}", expanded=False):
            if items:
                for it in items[:5]:
                    st.markdown(
                        f"- {it.title}  \n"
                        f"  <small style='color:gray'>{it.published_at[:16] if it.published_at else ''} · {it.source}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("近 24 小时无相关新闻")

# === Bottom: AI Summary ===
st.markdown("---")
st.subheader("AI 投研摘要")

if briefing and briefing.get("analyst_result"):
    ar = briefing["analyst_result"]
    st.caption(f"{ar.get('model', '?')} · {ar.get('analysis_time', '')[:16]}")
    st.markdown(ar.get("analysis", ""))
else:
    latest = load_all_analyses()
    if latest:
        a = latest[0]
        st.caption(f"{a.model} · {a.analysis_time[:16]} · {a.news_count_input} 条新闻")
        st.markdown(a.analysis)
    else:
        st.info("点击上方「生成今日早报」获取 AI 分析。")
