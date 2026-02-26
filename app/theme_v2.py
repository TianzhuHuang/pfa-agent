"""
PFA v2 视觉系统 — Sharesight 风格

设计原则:
  - 白底极淡灰 (#F8F9FA) 背景
  - 白色纯色卡片容器
  - Inter / Helvetica 字体
  - 极细线条表格
  - 色彩仅用于涨跌 (红 #dc3545 / 绿 #28a745)
  - 克制、专业、数据驱动
"""

import streamlit as st

# A-share: red = up, green = down
COLORS = {
    "up": "#dc3545",
    "down": "#28a745",
    "neutral": "#6c757d",
    "bg": "#F8F9FA",
    "card": "#FFFFFF",
    "text": "#333333",
    "text_secondary": "#666666",
    "text_muted": "#999999",
    "border": "#E9ECEF",
    "accent": "#0066FF",
    "accent_light": "#E8F0FE",
}


def inject_v2_theme():
    """Inject Sharesight-style global CSS."""
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global reset */
    .stApp {
        background-color: #F8F9FA;
        font-family: 'Inter', -apple-system, 'Helvetica Neue', sans-serif;
    }
    * { font-family: 'Inter', -apple-system, 'Helvetica Neue', sans-serif !important; }

    /* Hide default Streamlit sidebar completely */
    [data-testid="stSidebar"] { display: none !important; }
    .stApp > header { display: none !important; }

    /* Typography */
    h1 { font-size: 24px; font-weight: 700; color: #333; letter-spacing: -0.3px; margin-bottom: 4px; }
    h2 { font-size: 18px; font-weight: 600; color: #333; }
    h3 { font-size: 15px; font-weight: 600; color: #333; }
    p, span, li, td, th, label, div { color: #333; }

    /* Cards */
    .v2-card {
        background: #FFFFFF;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .v2-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.04); }

    /* Metric cards */
    .v2-metric {
        background: #FFFFFF;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: left;
    }
    .v2-metric .label { font-size: 12px; color: #999; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .v2-metric .value { font-size: 28px; font-weight: 700; color: #333; margin-top: 4px; }
    .v2-metric .change { font-size: 14px; font-weight: 600; margin-top: 2px; }

    /* Tables — Sharesight style: thin horizontal lines only */
    .v2-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .v2-table th {
        text-align: left; padding: 10px 12px; font-size: 12px; font-weight: 600;
        color: #999; text-transform: uppercase; letter-spacing: 0.5px;
        border-bottom: 2px solid #E9ECEF; background: transparent;
    }
    .v2-table th.right { text-align: right; }
    .v2-table td {
        padding: 12px; border-bottom: 1px solid #F0F0F0; color: #333;
        vertical-align: middle; white-space: nowrap;
    }
    .v2-table td.right { text-align: right; }
    .v2-table tr:hover td { background: #FAFBFC; }
    .v2-table .sym { color: #0066FF; font-weight: 600; cursor: pointer; text-decoration: none; }
    .v2-table .sym:hover { text-decoration: underline; }
    .v2-table .up { color: #dc3545; font-weight: 600; }
    .v2-table .down { color: #28a745; font-weight: 600; }

    /* Top navigation bar */
    .v2-topnav {
        background: #FFFFFF;
        border-bottom: 1px solid #E9ECEF;
        padding: 12px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -1rem -1rem 24px -1rem;
        position: sticky; top: 0; z-index: 999;
    }
    .v2-topnav .logo { font-size: 18px; font-weight: 700; color: #333; }
    .v2-topnav .nav-links { display: flex; gap: 24px; }
    .v2-topnav .nav-links a {
        color: #666; text-decoration: none; font-size: 14px; font-weight: 500;
        padding: 6px 0; border-bottom: 2px solid transparent;
    }
    .v2-topnav .nav-links a:hover { color: #333; }
    .v2-topnav .nav-links a.active { color: #0066FF; border-bottom-color: #0066FF; }
    .v2-topnav .user-info { font-size: 13px; color: #999; }

    /* Chat bubble styling */
    [data-testid="stChatMessage"] {
        background: #FFFFFF !important;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        margin-bottom: 8px;
    }
    [data-testid="stChatInput"] textarea {
        border: 1px solid #E9ECEF !important;
        border-radius: 8px !important;
    }

    /* Buttons */
    .stButton > button {
        border: 1px solid #E9ECEF;
        border-radius: 6px;
        font-weight: 500;
    }
    .stButton > button[kind="primary"] {
        background: #0066FF;
        color: white;
        border: none;
    }

    /* Inputs */
    .stTextInput > div > div > input {
        border: 1px solid #E9ECEF !important;
        border-radius: 6px !important;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: transparent; gap: 0; }
    .stTabs [data-baseweb="tab"] {
        color: #666; font-weight: 500; padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #0066FF !important; border-bottom-color: #0066FF !important;
    }

    /* Data frames */
    [data-testid="stDataFrame"] { background: #FFFFFF !important; border: 1px solid #E9ECEF !important; border-radius: 8px !important; }

    /* Empty state */
    .v2-empty {
        text-align: center; padding: 60px 20px;
        color: #999; font-size: 16px;
    }
    .v2-empty .icon { font-size: 48px; margin-bottom: 16px; }
    .v2-empty .title { font-size: 20px; font-weight: 600; color: #333; margin-bottom: 8px; }

    /* Login page */
    .v2-login-box {
        max-width: 400px; margin: 80px auto; background: #FFFFFF;
        border: 1px solid #E9ECEF; border-radius: 12px; padding: 40px;
    }
    .v2-login-box .logo { text-align: center; font-size: 24px; font-weight: 700; margin-bottom: 8px; }
    .v2-login-box .subtitle { text-align: center; color: #999; font-size: 14px; margin-bottom: 32px; }
</style>""", unsafe_allow_html=True)


def render_topnav(active: str = "portfolio", user_email: str = "", show_logout: bool = True):
    """Render the top navigation bar."""
    from html import escape

    def nav_class(name):
        return "active" if name == active else ""

    logout_html = ""
    if show_logout and user_email:
        logout_html = f'<span class="user-info">{escape(user_email)} · <a href="/?logout=1" style="color:#dc3545;">退出</a></span>'

    st.markdown(f"""
<div class="v2-topnav">
    <div style="display:flex; align-items:center; gap:32px;">
        <span class="logo">PFA</span>
        <div class="nav-links">
            <a href="/" class="{nav_class('portfolio')}">Portfolio</a>
            <a href="/综合早报" class="{nav_class('briefing')}">Briefing</a>
            <a href="/分析中心" class="{nav_class('analysis')}">Analysis</a>
            <a href="/数据源配置" class="{nav_class('settings')}">Settings</a>
        </div>
    </div>
    {logout_html}
</div>""", unsafe_allow_html=True)
