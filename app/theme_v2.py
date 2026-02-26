"""
PFA v2 设计系统 — 专业金融终端风格

参考: Sharesight + Bloomberg + Robinhood
规范: docs/ui-design-system.md
"""

import streamlit as st
from html import escape

# Design tokens
COLORS = {
    # Dark mode (primary)
    "bg": "#0F1116",
    "bg2": "#1A1D26",
    "bg3": "#242832",
    "border": "#2D3139",
    "text": "#E8EAED",
    "text2": "#9AA0A6",
    "text3": "#5F6368",
    # Semantic
    "up": "#E53935",
    "down": "#43A047",
    "accent": "#4285F4",
    "accent_bg": "rgba(66,133,244,0.12)",
    "warning": "#FB8C00",
    "info": "#29B6F6",
}


def inject_v2_theme():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* === GLOBAL === */
    .stApp { background: #0F1116 !important; }
    * { font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important; }
    [data-testid="stSidebar"] { display: none !important; }
    .stApp > header { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0F1116; }
    ::-webkit-scrollbar-thumb { background: #2D3139; border-radius: 3px; }

    /* === TYPOGRAPHY === */
    h1 { font-size: 20px !important; font-weight: 600 !important; color: #E8EAED !important; margin-bottom: 4px !important; }
    h2 { font-size: 16px !important; font-weight: 600 !important; color: #E8EAED !important; }
    h3 { font-size: 14px !important; font-weight: 600 !important; color: #9AA0A6 !important; text-transform: uppercase; letter-spacing: 0.5px; }
    p, span, li, div, label { color: #E8EAED; }
    a { color: #4285F4 !important; text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }

    /* === METRIC CARD === */
    .metric-card {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 16px 20px;
    }
    .metric-card .label {
        font-size: 11px; font-weight: 500; color: #5F6368;
        text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;
    }
    .metric-card .value {
        font-size: 28px; font-weight: 700; color: #E8EAED;
        font-variant-numeric: tabular-nums;
    }
    .metric-card .change { font-size: 14px; font-weight: 600; margin-top: 2px; }
    .metric-card .up { color: #E53935; }
    .metric-card .down { color: #43A047; }

    /* === HOLDINGS TABLE === */
    .fin-table { width: 100%; border-collapse: collapse; }
    .fin-table th {
        font-size: 11px; font-weight: 600; color: #5F6368;
        text-transform: uppercase; letter-spacing: 0.5px;
        padding: 8px 12px; text-align: left;
        border-bottom: 1px solid #2D3139;
    }
    .fin-table th.r { text-align: right; }
    .fin-table td {
        font-size: 14px; color: #E8EAED; padding: 10px 12px;
        border-bottom: 1px solid rgba(45,49,57,0.5);
        font-variant-numeric: tabular-nums; white-space: nowrap;
    }
    .fin-table td.r { text-align: right; }
    .fin-table tr:hover td { background: #242832; }
    .fin-table .sym { color: #4285F4; font-weight: 600; cursor: pointer; text-decoration: none; }
    .fin-table .sym:hover { text-decoration: underline; }
    .fin-table .up { color: #E53935; }
    .fin-table .down { color: #43A047; }
    .fin-table .muted { color: #5F6368; }
    .fin-table .group-row td, .fin-table tr.group-row td {
        font-size: 11px; font-weight: 600; color: #5F6368;
        padding: 10px 12px; background: #1A1D26 !important;
        border-bottom: 1px solid #2D3139;
        letter-spacing: 0.3px; text-transform: uppercase;
    }

    /* === TOP NAV === */
    .topnav {
        background: #1A1D26; border-bottom: 1px solid #2D3139;
        padding: 0 24px; display: flex; align-items: center;
        justify-content: space-between; height: 52px;
        margin: -1rem -1rem 24px -1rem;
        position: sticky; top: 0; z-index: 999;
    }
    .topnav .logo { font-size: 18px; font-weight: 700; color: #E8EAED; letter-spacing: -0.5px; }
    .topnav .nav { display: flex; gap: 0; height: 52px; }
    .topnav .nav a {
        color: #9AA0A6; text-decoration: none !important; font-size: 13px; font-weight: 500;
        padding: 0 16px; display: flex; align-items: center; height: 100%;
        border-bottom: 2px solid transparent;
    }
    .topnav .nav a:hover { color: #E8EAED; background: rgba(255,255,255,0.04); }
    .topnav .nav a.on { color: #4285F4; border-bottom-color: #4285F4; }
    .topnav .user { font-size: 12px; color: #5F6368; }
    .topnav .user a { color: #E53935 !important; margin-left: 8px; }

    /* === CARDS === */
    .card {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 20px; margin-bottom: 16px;
    }

    /* === CHAT === */
    [data-testid="stChatMessage"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important;
        border-radius: 12px !important; margin-bottom: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: #1A1D26 !important; color: #E8EAED !important;
        border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }
    [data-testid="stChatInput"] button { background: #4285F4 !important; }

    /* === INPUTS === */
    .stTextInput > div > div > input {
        background: #1A1D26 !important; color: #E8EAED !important;
        border: 1px solid #2D3139 !important; border-radius: 6px !important;
    }
    .stTextInput > div > div > input::placeholder { color: #5F6368 !important; }
    .stNumberInput > div > div > input { background: #1A1D26 !important; color: #E8EAED !important; }
    .stSelectbox > div > div { background: #1A1D26 !important; color: #E8EAED !important; }

    /* === BUTTONS === */
    .stButton > button {
        background: transparent; color: #E8EAED; border: 1px solid #2D3139;
        border-radius: 6px; font-weight: 500;
    }
    .stButton > button:hover { background: #242832; border-color: #4285F4; }
    .stButton > button[kind="primary"] {
        background: #4285F4 !important; color: white !important; border: none !important;
    }
    .stButton > button[kind="primary"]:hover { background: #3367D6 !important; }

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] { background: transparent; }
    .stTabs [data-baseweb="tab"] { color: #9AA0A6; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #4285F4 !important; }

    /* === EXPANDER === */
    [data-testid="stExpander"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary { color: #E8EAED !important; }

    /* === DATA FRAMES === */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }

    /* === LOGIN === */
    .login-box {
        max-width: 400px; margin: 100px auto;
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 12px;
        padding: 40px; text-align: center;
    }
    .login-box .logo { font-size: 28px; font-weight: 700; color: #E8EAED; margin-bottom: 4px; }
    .login-box .sub { font-size: 13px; color: #5F6368; margin-bottom: 32px; }

    /* === EMPTY STATE === */
    .empty-state { text-align: center; padding: 80px 20px; }
    .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.6; }
    .empty-state .title { font-size: 20px; font-weight: 600; color: #E8EAED; margin-bottom: 8px; }
    .empty-state .desc { font-size: 14px; color: #5F6368; }

    /* === ONBOARDING CARDS === */
    .onboard-card {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 24px; text-align: center; cursor: pointer;
        transition: border-color 0.2s;
    }
    .onboard-card:hover { border-color: #4285F4; }
    .onboard-card .icon { font-size: 32px; margin-bottom: 8px; }
    .onboard-card .title { font-size: 14px; font-weight: 600; color: #E8EAED; }
    .onboard-card .desc { font-size: 12px; color: #5F6368; margin-top: 4px; }

    /* === CONTAINER HEIGHT === */
    [data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
</style>""", unsafe_allow_html=True)


def render_topnav(active: str = "portfolio", user_email: str = ""):
    """Render professional top navigation bar."""
    def c(name):
        return "on" if name == active else ""

    user_html = ""
    if user_email:
        user_html = f'<span class="user">{escape(user_email)} <a href="/?logout=1">退出</a></span>'

    st.markdown(f"""
<div class="topnav">
    <div style="display:flex;align-items:center;">
        <span class="logo">PFA</span>
        <div class="nav" style="margin-left:32px;">
            <a href="/" class="{c('portfolio')}">Portfolio</a>
            <a href="/综合早报" class="{c('briefing')}">Briefing</a>
            <a href="/分析中心" class="{c('analysis')}">Analysis</a>
            <a href="/数据源配置" class="{c('settings')}">Settings</a>
        </div>
    </div>
    {user_html}
</div>""", unsafe_allow_html=True)
