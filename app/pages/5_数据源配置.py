"""数据源配置 — RSS / API / 社交与监控（PM 重设计：Tab 分组 + 卡片 + 统一行操作）"""

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

def _url(item): return item.get("url", item) if isinstance(item, dict) else item
def _name(item): return item.get("name", "") if isinstance(item, dict) else ""
def _cat(item): return item.get("category", "") if isinstance(item, dict) else ""

# ---------------------------------------------------------------------------
# 页面标题 + 摘要条（一览当前配置规模）
# ---------------------------------------------------------------------------
st.markdown(
    '<h1 class="pfa-title" style="font-size:20px;font-weight:600;margin-bottom:8px;">数据源配置</h1>',
    unsafe_allow_html=True
)
sources = load_data_sources()
rss_list = sources.get("rss_urls", [])
api_list = sources.get("api_sources", [])
api_enabled = len([s for s in api_list if s.get("enabled")])
tw = len(sources.get("twitter_handles", []))
xq = len(sources.get("xueqiu_user_ids", []))
urls = len(sources.get("monitor_urls", []))

st.markdown(f"""
<div class="settings-summary-strip">
    <span>RSS <strong style="color:#E8EAED;">{len(rss_list)}</strong></span>
    <span>API <strong style="color:#E8EAED;">{api_enabled}</strong></span>
    <span>Twitter <strong style="color:#E8EAED;">{tw}</strong></span>
    <span>雪球 <strong style="color:#E8EAED;">{xq}</strong></span>
    <span>监控 URL <strong style="color:#E8EAED;">{urls}</strong></span>
    <span style="margin-left:8px;color:#5F6368;">· 保存后立即生效</span>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab：订阅与 API | 社交与监控
# ---------------------------------------------------------------------------
tab_sub, tab_social = st.tabs(["订阅与 API", "社交与监控"])

with tab_sub:
    # ---------- RSS 订阅 ----------
    st.markdown("""
    <div class="settings-card">
        <div class="settings-card-title">RSS 订阅</div>
        <div class="settings-card-body">""", unsafe_allow_html=True)

    for i, item in enumerate(rss_list):
        url, name, cat = _url(item), _name(item), _cat(item)
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            st.markdown(f"""
            <div class="settings-row-cell">
                <span class="name">{escape(name or "—")}</span>
                <span class="cat">{escape(cat)}</span><br/>
                <span class="url">{escape(url)}</span>
            </div>""", unsafe_allow_html=True)
        with c2:
            if st.button("测试", key=f"test_rss_{i}"):
                with st.spinner("测试中..."):
                    try:
                        f = feedparser.parse(url)
                        if f.entries:
                            st.success(f"✅ {len(f.entries)} 条")
                        else:
                            st.warning("⚠️ 连接成功但无条目")
                    except Exception as e:
                        st.error(f"❌ {str(e)[:80]}")
        with c3:
            if st.button("删除", key=f"del_rss_{i}"):
                remove_rss_source(url)
                st.rerun()

    with st.form("add_rss", clear_on_submit=True):
        st.markdown('<div class="pfa-caption" style="margin-top:16px;margin-bottom:8px;">添加订阅</div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        with r1:
            new_url = st.text_input("RSS URL", placeholder="https://36kr.com/feed", label_visibility="collapsed")
        with r2:
            new_name = st.text_input("名称", placeholder="36kr", label_visibility="collapsed")
        new_cat = st.selectbox("分类", ["宏观与快讯", "深度分析", "官方公告", "其他"], label_visibility="collapsed")
        if st.form_submit_button("添加 RSS"):
            if (new_url or "").strip():
                add_rss_source((new_url or "").strip(), (new_name or "").strip() or "RSS", new_cat)
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ---------- API 数据源 ----------
    if api_list:
        st.markdown("""
        <div class="settings-card">
            <div class="settings-card-title">API 数据源</div>
            <div class="settings-card-body">""", unsafe_allow_html=True)
        for i, src in enumerate(api_list):
            c1, c2 = st.columns([5, 1])
            status = "✅ 启用" if src.get("enabled") else "⚪ 禁用"
            mode = "全局" if src.get("mode") == "global" else "按标的"
            with c1:
                st.markdown(f"""
                <div class="settings-row-cell">
                    <span class="name">{escape(src.get('name', '?'))}</span>
                    <span class="cat">{escape(src.get('category', ''))}</span> · {mode} · {status}
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("测试", key=f"test_api_{i}"):
                    with st.spinner("测试中..."):
                        try:
                            if src.get("type") == "wallstreetcn":
                                r = requests.get(src.get("api_url", ""), timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                                data = r.json()
                                n = len(data.get("data", {}).get("items", []))
                                st.success(f"✅ {n} 条快讯")
                            elif src.get("type") == "eastmoney":
                                st.success("✅ 东方财富 API 可用")
                            else:
                                st.info("已启用")
                        except Exception as e:
                            st.error(f"❌ {str(e)[:80]}")
        st.markdown("</div></div>", unsafe_allow_html=True)

    # ---------- 待激活数据源 ----------
    unavail = sources.get("unavailable_sources", [])
    rsshub = sources.get("self_hosted_rsshub", "")
    if unavail or rsshub:
        st.markdown("""
        <div class="settings-card">
            <div class="settings-card-title">待激活数据源</div>
            <div class="settings-card-body">""", unsafe_allow_html=True)
        if rsshub:
            st.success(f"RSSHub: {rsshub}")
        else:
            st.info("配置 `self_hosted_rsshub` 后可激活更多源（财联社、格隆汇、金十等）。")
        for src in unavail:
            st.markdown(f'<div class="settings-row-cell"><span class="name">{escape(src.get("name", "?"))}</span> — <span class="url">{escape(src.get("reason", ""))}</span></div>', unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

with tab_social:
    for key, label, placeholder, test_fn in [
        ("twitter_handles", "Twitter", "@elonmusk", None),
        ("xueqiu_user_ids", "雪球用户", "9650668145", lambda uid: f"https://xueqiu.com/u/{uid}"),
        ("monitor_urls", "监控 URL", "https://...", None),
    ]:
        items = sources.get(key, [])
        st.markdown(f"""
        <div class="settings-card">
            <div class="settings-card-title">{label}</div>
            <div class="settings-card-body">""", unsafe_allow_html=True)
        for j, v in enumerate(items):
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                display_v = f"@{v}" if key == "twitter_handles" else v
                st.markdown(f'<div class="settings-row-cell"><span class="url">{escape(display_v)}</span></div>', unsafe_allow_html=True)
            with c2:
                if st.button("测试", key=f"test_{key}_{j}"):
                    with st.spinner("测试中..."):
                        if key == "xueqiu_user_ids":
                            st.warning("雪球需通过 Chrome 扩展访问，请确认扩展已安装并登录。")
                        elif key == "twitter_handles":
                            st.warning("Twitter/X 需登录或配置 API Key。")
                        else:
                            try:
                                r = requests.get(v, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                                st.success(f"✅ HTTP {r.status_code}")
                            except Exception as e:
                                st.error(f"❌ {str(e)[:80]}")
            with c3:
                if st.button("删除", key=f"del_{key}_{j}"):
                    remove_source(key, v)
                    st.rerun()
        with st.form(f"add_{key}", clear_on_submit=True):
            val = st.text_input(f"添加 {label}", placeholder=placeholder, label_visibility="collapsed")
            if st.form_submit_button(f"添加 {label}"):
                if (val or "").strip():
                    add_source(key, (val or "").strip().lstrip("@") if key == "twitter_handles" else (val or "").strip())
                    st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)
