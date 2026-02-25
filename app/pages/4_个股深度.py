"""个股深度 (Ticker Detail) — 基本面 + 新闻流 + Ask Agent 交互"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import requests
from pfa.data.store import load_all_feed_items
from agents.secretary_agent import load_portfolio, fetch_single_symbol

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.header("个股深度")

if not holdings:
    st.warning("请先添加持仓。")
    st.stop()

# --- Stock selector ---
sym_map = {f"{h['name']} ({h['symbol']}.{h.get('market','?')})": h for h in holdings}
selected = st.selectbox("选择标的", list(sym_map.keys()))
h = sym_map[selected]
sym, name, market = h["symbol"], h.get("name", h["symbol"]), h.get("market", "?")

# Fetch latest news for this stock
if st.button("刷新数据", use_container_width=True):
    with st.spinner(f"Scout 抓取 {name}..."):
        fetch_single_symbol(sym, name, market, 72)
    st.rerun()

# === Three-column layout ===
col_info, col_news, col_chat = st.columns([1, 1.5, 1.5])

# --- Left: Basic info ---
with col_info:
    st.subheader("基本面")

    cost = h.get("cost_price", "—")
    qty = h.get("quantity", "—")
    acct = h.get("account", "—")
    src = h.get("source", "—")

    st.markdown(f"""
| 项目 | 值 |
|---|---|
| **代码** | {sym} |
| **名称** | {name} |
| **市场** | {market} |
| **成本价** | {cost} |
| **持仓量** | {qty} |
| **账户** | {acct} |
| **录入来源** | {src} |
""")

    # Try to get real-time quote from Xueqiu
    try:
        from pfa.browser_fetcher import fetch_xueqiu_quote
        xq_sym = f"{'SH' if market == 'A' and sym.startswith('6') else 'SZ' if market == 'A' else 'HK' if market == 'HK' else ''}{sym}"
        quotes = fetch_xueqiu_quote([xq_sym])
        if quotes:
            q = quotes[0]
            st.metric("实时价格", f"{q['current']}", f"{q['percent']}%")
    except Exception:
        pass

# --- Middle: News feed ---
with col_news:
    st.subheader("新闻流")

    items = load_all_feed_items(symbol=sym, since_hours=72)
    if items:
        st.caption(f"近 72h 共 {len(items)} 条")
        for it in items[:15]:
            source_tag = it.source
            if it.source == "rss" and it.source_id:
                source_tag = it.source_id
            st.markdown(
                f"**[{it.title}]({it.url})**  \n"
                f"<small style='color:gray'>{it.published_at[:16] if it.published_at else ''} · {source_tag}</small>  \n"
                f"<small>{it.content_snippet[:100] if it.content_snippet else ''}</small>",
                unsafe_allow_html=True,
            )
            st.markdown("---")
    else:
        st.info("暂无新闻。点击上方「刷新数据」抓取。")

# --- Right: Ask Agent chat ---
with col_chat:
    st.subheader("Ask Agent")
    st.caption(f"基于 {name} 的最新新闻，向 AI 提问获取投研观点")

    if f"chat_{sym}" not in st.session_state:
        st.session_state[f"chat_{sym}"] = []

    chat_history = st.session_state[f"chat_{sym}"]

    # Display chat history
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input(f"关于{name}，你想了解什么？")

    if user_input:
        chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Build context from recent news
        news_items = load_all_feed_items(symbol=sym, since_hours=72)
        news_context = "\n".join(
            f"- [{it.published_at[:16] if it.published_at else ''}] {it.title}: {it.content_snippet[:150]}"
            for it in news_items[:10]
        )

        prompt = (
            f"你是一位专业投研分析师，专门跟踪 {name}({sym}.{market})。\n\n"
            f"以下是该标的近期的新闻动态：\n{news_context}\n\n"
            f"用户持仓信息：成本价 {cost}，持仓量 {qty}。\n\n"
            f"用户的问题：{user_input}\n\n"
            f"请基于上述新闻给出专业、客观的投资分析观点。"
            f"使用中文回答，简洁但有深度。"
        )

        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if api_key:
            with st.chat_message("assistant"):
                with st.spinner("分析中..."):
                    try:
                        resp = requests.post(
                            DASHSCOPE_URL,
                            headers={"Authorization": f"Bearer {api_key}",
                                     "Content-Type": "application/json"},
                            json={"model": "qwen-plus",
                                  "messages": [{"role": "user", "content": prompt}],
                                  "temperature": 0.4, "max_tokens": 1500},
                            timeout=60,
                        )
                        resp.raise_for_status()
                        answer = resp.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        answer = f"分析失败: {e}"
                st.markdown(answer)
            chat_history.append({"role": "assistant", "content": answer})
        else:
            st.error("需要 DASHSCOPE_API_KEY 才能使用 Ask Agent")
