"""投研看板页 — 持仓列表 + 新闻 + 深度分析"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_feed_items, load_all_analyses

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

# --- Sidebar: fetch & analyze controls ---
with st.sidebar:
    st.subheader("数据操作")
    hours = st.selectbox("时间窗口", [24, 48, 72, 168], index=2, format_func=lambda h: f"{h} 小时")
    col1, col2 = st.columns(2)
    fetch_btn = col1.button("抓取新闻", use_container_width=True)
    analyze_btn = col2.button("深度分析", use_container_width=True)

    if fetch_btn or analyze_btn:
        cmd = [sys.executable, str(ROOT / "scripts" / "fetch_holding_news.py"),
               "--hours", str(hours)]
        if analyze_btn:
            cmd.append("--analyze")
        with st.spinner("正在抓取..." if not analyze_btn else "正在抓取 + 分析..."):
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    cwd=str(ROOT), timeout=120,
                                    env={**os.environ})
        if result.returncode == 0:
            st.success("完成")
        else:
            st.error("执行出错")
        with st.expander("运行日志"):
            st.code(result.stdout + result.stderr, language="text")
        st.rerun()

# --- Layout: left = holdings + news, right = analysis ---
left, right = st.columns([1, 1])

# --- Left: holdings + news by symbol ---
with left:
    st.subheader("持仓 & 新闻")
    for h in holdings:
        sym = h.get("symbol", "?")
        name = h.get("name", sym)
        market = h.get("market", "?")

        with st.expander(f"**{name}** ({sym}.{market})", expanded=False):
            items = load_all_feed_items(symbol=sym, since_hours=72)
            if items:
                for it in items[:15]:
                    st.markdown(
                        f"- [{it.title}]({it.url})  \n"
                        f"  <small style='color:gray'>{it.published_at} · {it.source}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("近 72 小时无相关新闻")

# --- Right: latest analysis ---
with right:
    st.subheader("今日投研简报")
    analyses = load_all_analyses()
    if analyses:
        latest = analyses[0]
        st.caption(f"模型: {latest.model} · {latest.analysis_time[:16]} · {latest.news_count_input} 条新闻输入")
        st.markdown(latest.analysis)
    else:
        st.info("暂无分析记录。点击左侧「深度分析」按钮生成。")
