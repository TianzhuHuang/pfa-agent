"""数据源配置 — RSS / API / RSSHub 管理"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from agents.secretary_agent import (
    load_data_sources, add_rss_source, remove_rss_source,
    add_source, remove_source,
)


def _url(item): return item.get("url", item) if isinstance(item, dict) else item
def _name(item): return item.get("name", "") if isinstance(item, dict) else ""
def _cat(item): return item.get("category", "") if isinstance(item, dict) else ""


st.header("数据源配置")
st.caption("Scout Agent 数据抓取源管理")

sources = load_data_sources()

# RSS
st.subheader("RSS 订阅")
for item in sources.get("rss_urls", []):
    url, name, cat = _url(item), _name(item), _cat(item)
    c1, c2 = st.columns([5, 1])
    label = f"**{name}** " if name else ""
    c1.markdown(f"{label}`{url}` · {cat}" if cat else f"{label}`{url}`")
    if c2.button("删除", key=f"del_{url}"):
        remove_rss_source(url)
        st.rerun()

with st.form("add_rss", clear_on_submit=True):
    c1, c2 = st.columns([3, 1])
    new_url = c1.text_input("RSS URL", placeholder="https://36kr.com/feed")
    new_name = c2.text_input("名称", placeholder="36kr")
    new_cat = st.selectbox("分类", ["宏观与快讯", "深度分析", "官方公告", "其他"])
    if st.form_submit_button("添加 RSS"):
        if new_url.strip():
            add_rss_source(new_url, new_name, new_cat)
            st.rerun()

# API
for src in sources.get("api_sources", []):
    if not st.session_state.get("show_api"):
        break
    st.markdown(f"**{src.get('name')}** · {src.get('category')} · {'启用' if src.get('enabled') else '禁用'}")

# Twitter / Xueqiu / URLs
st.markdown("---")
for key, label, placeholder in [
    ("twitter_handles", "Twitter", "@elonmusk"),
    ("xueqiu_user_ids", "雪球用户", "1234567890"),
    ("monitor_urls", "监控 URL", "https://..."),
]:
    items = sources.get(key, [])
    st.subheader(label)
    for v in items:
        c1, c2 = st.columns([5, 1])
        c1.write(v)
        if c2.button("删除", key=f"del_{key}_{v}"):
            remove_source(key, v)
            st.rerun()
    with st.form(f"add_{key}", clear_on_submit=True):
        val = st.text_input(f"添加 {label}", placeholder=placeholder)
        if st.form_submit_button(f"添加"):
            if val.strip():
                add_source(key, val.strip().lstrip("@") if key == "twitter_handles" else val.strip())
                st.rerun()

# Summary
st.markdown("---")
rss_n = len(sources.get("rss_urls", []))
api_n = len([s for s in sources.get("api_sources", []) if s.get("enabled")])
st.caption(f"RSS:{rss_n} · API:{api_n} · Twitter:{len(sources.get('twitter_handles',[]))} · "
           f"雪球:{len(sources.get('xueqiu_user_ids',[]))} · URL:{len(sources.get('monitor_urls',[]))}")
