"""数据源配置 — 管理 RSS / Twitter / 监控 URL，实时同步到 config"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from agents.secretary_agent import load_data_sources, save_data_sources, add_source, remove_source

st.header("数据源配置")
st.caption("配置 Scout Agent 的数据抓取源，保存后立即生效。")

sources = load_data_sources()

# --- RSS ---
st.subheader("RSS 订阅")
rss_list = sources.get("rss_urls", [])
if rss_list:
    for url in rss_list:
        c1, c2 = st.columns([5, 1])
        c1.code(url, language=None)
        if c2.button("删除", key=f"del_rss_{url}"):
            remove_source("rss_urls", url)
            st.rerun()
else:
    st.caption("暂无 RSS 源")

with st.form("add_rss", clear_on_submit=True):
    new_rss = st.text_input("添加 RSS URL", placeholder="https://36kr.com/feed")
    if st.form_submit_button("添加 RSS"):
        if new_rss.strip():
            add_source("rss_urls", new_rss)
            st.success(f"已添加: {new_rss}")
            st.rerun()

st.markdown("---")

# --- Twitter ---
st.subheader("Twitter 账号")
tw_list = sources.get("twitter_handles", [])
if tw_list:
    for handle in tw_list:
        c1, c2 = st.columns([5, 1])
        c1.write(f"@{handle}")
        if c2.button("删除", key=f"del_tw_{handle}"):
            remove_source("twitter_handles", handle)
            st.rerun()
else:
    st.caption("暂无 Twitter 账号")

with st.form("add_twitter", clear_on_submit=True):
    new_tw = st.text_input("添加 Twitter 用户名", placeholder="elikishtain")
    if st.form_submit_button("添加 Twitter"):
        if new_tw.strip():
            add_source("twitter_handles", new_tw.strip().lstrip("@"))
            st.success(f"已添加: @{new_tw}")
            st.rerun()

st.markdown("---")

# --- Monitor URLs ---
st.subheader("监控网页 URL")
url_list = sources.get("monitor_urls", [])
if url_list:
    for url in url_list:
        c1, c2 = st.columns([5, 1])
        c1.code(url, language=None)
        if c2.button("删除", key=f"del_url_{url}"):
            remove_source("monitor_urls", url)
            st.rerun()
else:
    st.caption("暂无监控 URL")

with st.form("add_url", clear_on_submit=True):
    new_url = st.text_input("添加监控 URL", placeholder="https://xueqiu.com/u/1234567890")
    if st.form_submit_button("添加 URL"):
        if new_url.strip():
            add_source("monitor_urls", new_url)
            st.success(f"已添加: {new_url}")
            st.rerun()

st.markdown("---")

# --- Xueqiu ---
st.subheader("雪球用户")
xq_list = sources.get("xueqiu_user_ids", [])
if xq_list:
    for uid in xq_list:
        c1, c2 = st.columns([5, 1])
        c1.write(uid)
        if c2.button("删除", key=f"del_xq_{uid}"):
            remove_source("xueqiu_user_ids", uid)
            st.rerun()
else:
    st.caption("暂无雪球用户")

with st.form("add_xueqiu", clear_on_submit=True):
    new_xq = st.text_input("添加雪球用户 ID", placeholder="1234567890")
    if st.form_submit_button("添加雪球用户"):
        if new_xq.strip():
            add_source("xueqiu_user_ids", new_xq)
            st.success(f"已添加: {new_xq}")
            st.rerun()

# --- Summary ---
st.markdown("---")
st.caption(
    f"当前配置: {len(rss_list)} RSS · "
    f"{len(tw_list)} Twitter · "
    f"{len(url_list)} URL · "
    f"{len(xq_list)} 雪球"
)
