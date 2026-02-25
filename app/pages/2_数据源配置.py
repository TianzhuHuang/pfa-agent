"""数据源配置 — 管理 RSS / API / Twitter / URL，实时同步到 config"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from agents.secretary_agent import (
    load_data_sources, add_rss_source, remove_rss_source,
    add_source, remove_source,
)


def _rss_url(item) -> str:
    return item.get("url", item) if isinstance(item, dict) else item


def _rss_name(item) -> str:
    return item.get("name", "") if isinstance(item, dict) else ""


def _rss_category(item) -> str:
    return item.get("category", "") if isinstance(item, dict) else ""


def _rss_enabled(item) -> bool:
    return item.get("enabled", True) if isinstance(item, dict) else True


st.header("数据源配置")
st.caption("配置 Scout Agent 的数据抓取源，保存后立即生效。")

sources = load_data_sources()

# ===================================================================
# RSS Feeds
# ===================================================================
st.subheader("RSS 订阅")
rss_list = sources.get("rss_urls", [])
if rss_list:
    for item in rss_list:
        url = _rss_url(item)
        name = _rss_name(item)
        cat = _rss_category(item)
        enabled = _rss_enabled(item)
        label = f"**{name}** " if name else ""
        tag = f" · {cat}" if cat else ""
        status = "" if enabled else " (已禁用)"

        c1, c2 = st.columns([5, 1])
        c1.markdown(f"{label}`{url}`{tag}{status}")
        if c2.button("删除", key=f"del_rss_{url}"):
            remove_rss_source(url)
            st.rerun()
else:
    st.caption("暂无 RSS 源")

with st.form("add_rss", clear_on_submit=True):
    c1, c2 = st.columns([3, 1])
    new_url = c1.text_input("RSS URL", placeholder="https://36kr.com/feed")
    new_name = c2.text_input("名称（可选）", placeholder="36kr")
    new_cat = st.selectbox("分类", ["宏观与快讯", "深度分析", "官方公告", "其他"])
    if st.form_submit_button("添加 RSS"):
        if new_url.strip():
            add_rss_source(new_url, new_name, new_cat)
            st.success(f"已添加: {new_name or new_url}")
            st.rerun()

# ===================================================================
# API Sources (read-only display)
# ===================================================================
api_list = sources.get("api_sources", [])
if api_list:
    st.markdown("---")
    st.subheader("API 数据源")
    for src in api_list:
        status = "启用" if src.get("enabled", True) else "禁用"
        mode = "全局" if src.get("mode") == "global" else "按标的"
        st.markdown(
            f"**{src.get('name', '?')}** · {src.get('category', '')} · "
            f"{mode} · {status}"
        )
    st.caption("API 数据源由系统管理，如需修改请编辑 config/data-sources.json")

# ===================================================================
# Unavailable Sources (info)
# ===================================================================
unavail = sources.get("unavailable_sources", [])
rsshub_base = sources.get("self_hosted_rsshub", "")
if unavail:
    st.markdown("---")
    st.subheader("待激活数据源")
    if rsshub_base:
        st.success(f"RSSHub 实例: {rsshub_base}")
    else:
        st.info("以下源需要自建 RSSHub 实例后才能使用。设置 `self_hosted_rsshub` 后自动激活。")
    for src in unavail:
        st.markdown(
            f"- **{src.get('name', '?')}** — {src.get('reason', '')}"
        )

st.markdown("---")

# ===================================================================
# Twitter
# ===================================================================
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
    new_tw = st.text_input("Twitter 用户名", placeholder="elonmusk")
    if st.form_submit_button("添加 Twitter"):
        if new_tw.strip():
            add_source("twitter_handles", new_tw.strip().lstrip("@"))
            st.success(f"已添加: @{new_tw}")
            st.rerun()

st.markdown("---")

# ===================================================================
# Monitor URLs
# ===================================================================
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
    new_url = st.text_input("监控 URL", placeholder="https://xueqiu.com/u/1234567890")
    if st.form_submit_button("添加 URL"):
        if new_url.strip():
            add_source("monitor_urls", new_url)
            st.success(f"已添加: {new_url}")
            st.rerun()

st.markdown("---")

# ===================================================================
# Xueqiu
# ===================================================================
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
    new_xq = st.text_input("雪球用户 ID", placeholder="1234567890")
    if st.form_submit_button("添加雪球用户"):
        if new_xq.strip():
            add_source("xueqiu_user_ids", new_xq)
            st.success(f"已添加: {new_xq}")
            st.rerun()

# ===================================================================
# Summary
# ===================================================================
st.markdown("---")
api_count = len([s for s in api_list if s.get("enabled", True)])
st.caption(
    f"当前配置: {len(rss_list)} RSS · {api_count} API · "
    f"{len(tw_list)} Twitter · {len(url_list)} URL · "
    f"{len(xq_list)} 雪球 · {len(unavail)} 待激活"
)
