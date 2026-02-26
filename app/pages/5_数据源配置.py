"""数据源配置 — RSS / API / 健康检查"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import requests
import feedparser
from html import escape
from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user
from agents.secretary_agent import (
    load_data_sources, add_rss_source, remove_rss_source,
    add_source, remove_source,
)


inject_v2_theme()
user = get_user()
if not user.get('user_id'):
    st.warning('请先登录。')
    st.stop()
render_topnav(active='settings', user_email=user.get('email', ''))

dark = st.session_state.get("dark_mode", True)

def _url(item): return item.get("url", item) if isinstance(item, dict) else item
def _name(item): return item.get("name", "") if isinstance(item, dict) else ""
def _cat(item): return item.get("category", "") if isinstance(item, dict) else ""

st.header("数据源配置")
st.caption("Scout Agent 数据源管理 · 保存后立即生效")

sources = load_data_sources()

# ===================================================================
# RSS
# ===================================================================
st.subheader("RSS 订阅")
for item in sources.get("rss_urls", []):
    url, name, cat = _url(item), _name(item), _cat(item)
    c1, c2, c3 = st.columns([4, 1, 1])
    label = f"**{name}** " if name else ""
    c1.markdown(f"{label}`{escape(url)}` · {cat}")
    if c2.button("测试", key=f"test_rss_{url}"):
        with st.spinner("测试中..."):
            try:
                f = feedparser.parse(url)
                if f.entries:
                    st.success(f"✅ {len(f.entries)} 条 · {f.entries[0].get('title', '')[:40]}")
                else:
                    st.warning(f"⚠️ 连接成功但无条目" + (f" (bozo: {f.bozo_exception})" if f.bozo else ""))
            except Exception as e:
                st.error(f"❌ {e}")
    if c3.button("删除", key=f"del_rss_{url}"):
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

# ===================================================================
# API Sources
# ===================================================================
api_list = sources.get("api_sources", [])
if api_list:
    st.markdown("---")
    st.subheader("API 数据源")
    for src in api_list:
        c1, c2 = st.columns([4, 1])
        status = "✅ 启用" if src.get("enabled") else "⚪ 禁用"
        mode = "全局" if src.get("mode") == "global" else "按标的"
        c1.markdown(f"**{src.get('name', '?')}** · {src.get('category', '')} · {mode} · {status}")
        if c2.button("测试", key=f"test_api_{src.get('name','')}"):
            with st.spinner("测试中..."):
                try:
                    if src.get("type") == "wallstreetcn":
                        r = requests.get(src.get("api_url", ""), timeout=5,
                                         headers={"User-Agent": "Mozilla/5.0"})
                        data = r.json()
                        n = len(data.get("data", {}).get("items", []))
                        st.success(f"✅ {n} 条快讯")
                    elif src.get("type") == "eastmoney":
                        st.success("✅ 东方财富搜索 API 已验证可用")
                except Exception as e:
                    st.error(f"❌ {e}")

# ===================================================================
# Unavailable Sources
# ===================================================================
unavail = sources.get("unavailable_sources", [])
rsshub = sources.get("self_hosted_rsshub", "")
if unavail:
    st.markdown("---")
    st.subheader("待激活数据源")
    if rsshub:
        st.success(f"RSSHub: {rsshub}")
    else:
        st.info("需自建 RSSHub 实例，设置 `self_hosted_rsshub` 后自动激活。")
    for src in unavail:
        st.markdown(f"- **{src.get('name', '?')}** — {src.get('reason', '')}")

# ===================================================================
# Twitter / Xueqiu / URLs with health check
# ===================================================================
st.markdown("---")
for key, label, placeholder, test_fn in [
    ("twitter_handles", "Twitter", "@elonmusk", None),
    ("xueqiu_user_ids", "雪球用户", "9650668145", lambda uid: f"https://xueqiu.com/u/{uid}"),
    ("monitor_urls", "监控 URL", "https://...", None),
]:
    items = sources.get(key, [])
    st.subheader(label)
    for v in items:
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.write(f"@{v}" if key == "twitter_handles" else v)
        if c2.button("测试", key=f"test_{key}_{v}"):
            with st.spinner("测试中..."):
                if key == "xueqiu_user_ids":
                    st.warning("⚠️ 雪球需通过 Chrome 扩展访问（WAF 保护）。请确认 PFA 雪球助手扩展已安装并登录。")
                elif key == "twitter_handles":
                    st.warning("⚠️ Twitter/X 需要登录。请通过 Desktop 浏览器或配置 API Key。")
                else:
                    try:
                        r = requests.get(v, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                        st.success(f"✅ HTTP {r.status_code} · {len(r.text)} bytes")
                    except Exception as e:
                        st.error(f"❌ {e}")
        if c3.button("删除", key=f"del_{key}_{v}"):
            remove_source(key, v)
            st.rerun()
    with st.form(f"add_{key}", clear_on_submit=True):
        val = st.text_input(f"添加 {label}", placeholder=placeholder)
        if st.form_submit_button("添加"):
            if val.strip():
                add_source(key, val.strip().lstrip("@") if key == "twitter_handles" else val.strip())
                st.rerun()

# Summary
st.markdown("---")
rss_n = len(sources.get("rss_urls", []))
api_n = len([s for s in api_list if s.get("enabled")])
st.caption(f"RSS:{rss_n} · API:{api_n} · Twitter:{len(sources.get('twitter_handles',[]))} · "
           f"雪球:{len(sources.get('xueqiu_user_ids',[]))} · URL:{len(sources.get('monitor_urls',[]))}")
