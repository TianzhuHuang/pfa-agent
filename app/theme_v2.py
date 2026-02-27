"""
PFA v2 设计系统 — 专业金融终端风格

参考: Sharesight + Bloomberg + 雪盈 + TradingView（图表与信息结构）
规范: docs/ui-design-system.md
"""

import streamlit as st
from html import escape

# Design tokens（主色 #4285F4 即品牌色，全产品统一）
COLORS = {
    "brand": "#4285F4",
    "brand_bg": "rgba(66,133,244,0.12)",
    # Dark mode (primary)
    "bg": "#0F1116",
    "bg2": "#1A1D26",
    "bg3": "#242832",
    "border": "#2D3139",
    "text": "#E8EAED",
    "text2": "#9AA0A6",
    "text3": "#5F6368",
    # Card/border (for pages using dark_mode toggle)
    "border_dark": "#2D3139",
    "border_light": "#E0E0E0",
    "bg_card_dark": "#1A1D26",
    "bg_card_light": "#F8F9FA",
    # Semantic (A-share: red=up, green=down)
    "up": "#E53935",
    "down": "#43A047",
    "bullish": "#E53935",
    "bearish": "#43A047",
    "neutral": "#5F6368",
    "positive": "#E53935",
    "negative": "#43A047",
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

    /* === TYPOGRAPHY (unified scale: 12 / 14 / 16 / 20 / 24) === */
    h1 { font-size: 20px !important; font-weight: 600 !important; color: #E8EAED !important; margin-bottom: 8px !important; }
    h2 { font-size: 16px !important; font-weight: 600 !important; color: #E8EAED !important; margin-bottom: 8px !important; }
    h3 { font-size: 14px !important; font-weight: 600 !important; color: #9AA0A6 !important; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px !important; }
    p, span, li, div, label { font-size: 14px; color: #E8EAED; line-height: 1.6; }
    a { color: #4285F4 !important; text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }
    .pfa-caption { font-size: 12px !important; font-weight: 500 !important; color: #5F6368 !important; }
    .pfa-body { font-size: 14px !important; font-weight: 400 !important; color: #E8EAED !important; }
    .pfa-title { font-size: 16px !important; font-weight: 600 !important; color: #E8EAED !important; }
    .pfa-display { font-size: 24px !important; font-weight: 700 !important; font-variant-numeric: tabular-nums !important; }

    /* === METRIC CARD (Sharesight: 极细线/轻阴影，无厚重边框) === */
    .metric-card {
        background: #1A1D26; border: 1px solid #2D2D2D; border-radius: 8px;
        padding: 16px; min-height: 104px; box-sizing: border-box;
        display: flex; flex-direction: column; justify-content: flex-start;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .metric-card .label {
        font-size: 12px; font-weight: 500; color: #5F6368;
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
    }
    .metric-card .value {
        font-size: 24px; font-weight: 700; color: #E8EAED;
        font-variant-numeric: tabular-nums;
    }
    .metric-card .change { font-size: 14px; font-weight: 600; margin-top: 2px; }
    .metric-card .up { color: #E53935; }
    .metric-card .down { color: #43A047; }
    .metric-card .sparkline { margin-top: 6px; height: 20px; }
    .metric-card .sparkline svg { width: 100%; height: 20px; }
    .fin-table .ai-tag { font-size: 10px; margin-left: 4px; padding: 1px 5px; border-radius: 4px; }
    .fin-table .ai-tag.hot { background: rgba(229,57,53,0.15); color: #E53935; }
    .fin-table .ai-tag.high { background: rgba(251,140,0,0.15); color: #FB8C00; }

    /* === HOLDINGS TABLE (Sharesight: 表头 12px 中灰，盈亏仅数值着色) === */
    .fin-table { width: 100%; border-collapse: collapse; background: #1A1D26; }
    .fin-table th {
        font-size: 12px; font-weight: 600; color: #5F6368;
        text-transform: uppercase; letter-spacing: 0.5px;
        padding: 8px 12px; text-align: left;
        border-bottom: 1px solid #2D2D2D;
        background: #1A1D26;
        line-height: 1.4;
    }
    .fin-table th.r { text-align: right; }
    .fin-table td {
        font-size: 14px; color: #E8EAED; padding: 10px 12px;
        border-bottom: 1px solid #2D2D2D;
        font-variant-numeric: tabular-nums; white-space: nowrap;
        line-height: 1.4;
    }
    .fin-table td.r { text-align: right; }
    .fin-table tr:hover td { background: rgba(255,255,255,0.03); }
    .fin-table .sym { color: #4285F4; font-weight: 600; cursor: pointer; text-decoration: none; }
    .fin-table .sym:hover { text-decoration: underline; }
    .fin-table .up { color: #E53935; }
    .fin-table .down { color: #43A047; }
    .fin-table .muted { color: #5F6368; }
    .fin-table .group-row td, .fin-table tr.group-row td {
        font-size: 12px; font-weight: 600; color: #5F6368;
        padding: 10px 12px; background: #1A1D26 !important;
        border-bottom: 1px solid #2D2D2D;
        letter-spacing: 0.3px; text-transform: uppercase;
    }
    /* TradingView-style: 代码列突出为标的徽章 */
    .fin-table .ticker-badge {
        display: inline-block; font-size: 13px; font-weight: 600; color: #4285F4;
        padding: 2px 8px; border-radius: 4px; background: rgba(66,133,244,0.12);
        text-decoration: none; font-variant-numeric: tabular-nums;
        line-height: 1.4;
    }
    .fin-table .ticker-badge:hover { background: rgba(66,133,244,0.2); text-decoration: underline; }

    .fin-table .timeline-link {
        font-size: 12px;
        margin-left: 4px;
        color: #5F6368;
    }
    .fin-table .timeline-link:hover {
        color: #E8EAED;
        text-decoration: none;
    }

    /* === TRADINGVIEW-STYLE: 方向标签、观点卡片、图表面板 === */
    .direction-pill { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; margin-left: 8px; }
    .direction-pill.long, .direction-pill.做多 { background: rgba(229,57,53,0.15); color: #E53935; }
    .direction-pill.short, .direction-pill.做空 { background: rgba(67,160,71,0.15); color: #43A047; }
    .direction-pill.neutral { background: rgba(95,99,104,0.2); color: #9AA0A6; }
    .tv-section { margin-bottom: 24px; }
    .tv-section-title { font-size: 12px; font-weight: 600; color: #5F6368; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #2D3139; }
    .tv-view-card {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
        transition: border-color 0.15s, background 0.15s;
    }
    .tv-view-card:hover { border-color: #242832; background: #242832; }
    .tv-view-card-link { cursor: pointer; }
    .tv-view-card-link:hover .tv-view-card { border-color: #4285F4; background: #242832; }
    .tv-view-card .tv-card-header { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
    .tv-view-card .tv-card-symbol { font-size: 13px; font-weight: 600; color: #4285F4; }
    .tv-view-card .tv-card-title { font-size: 14px; font-weight: 600; color: #E8EAED; margin-bottom: 4px; }
    .tv-view-card .tv-card-meta { font-size: 12px; color: #5F6368; }
    .tv-view-card .tv-card-snippet { font-size: 14px; color: #9AA0A6; line-height: 1.5; margin-top: 6px; }
    .chart-panel {
        background: #1A1D26; border: 1px solid #2D2D2D; border-radius: 8px;
        overflow: hidden; margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .chart-panel .chart-panel-title { font-size: 12px; font-weight: 600; color: #5F6368; text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 16px; border-bottom: 1px solid #2D2D2D; }
    .chart-panel .chart-panel-body { padding: 12px; }
    .market-movers { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .market-movers .mover-badge { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 4px; background: #242832; border: 1px solid #2D3139; color: #E8EAED; }
    .market-movers .mover-badge.up { color: #E53935; }
    .market-movers .mover-badge.down { color: #43A047; }
    .move-grid { display: grid; gap: 8px; }
    @media (min-width: 640px) { .move-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); } }

    /* === CAPTION / 导航栏右侧说明（统一 12px Caption，深色背景下灰字可读） === */
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        font-size: 12px !important; font-weight: 500 !important; color: #9AA0A6 !important; line-height: 1.4 !important;
    }
    /* stText：禁止白底灰字 */
    [data-testid="stText"] { color: #E8EAED !important; }
    [data-testid="stText"] * { color: #E8EAED !important; }

    /* === TOP NAV === */
    .topnav {
        background: #1A1D26; border-bottom: 1px solid #2D3139;
        padding: 0 24px; display: flex; align-items: center;
        justify-content: space-between; height: 48px;
        margin: -1rem -1rem 24px -1rem;
        position: sticky; top: 0; z-index: 999;
    }
    .topnav .logo { font-size: 16px; font-weight: 600; color: #E8EAED; letter-spacing: -0.5px; }
    .topnav .nav { display: flex; gap: 0; height: 48px; }
    .topnav .nav a {
        color: #9AA0A6; text-decoration: none !important; font-size: 14px; font-weight: 500;
        padding: 0 16px; display: flex; align-items: center; height: 100%;
        border-bottom: 2px solid transparent;
    }
    .topnav .nav a:hover { color: #E8EAED; background: rgba(255,255,255,0.04); }
    .topnav .nav a.on { color: #4285F4; border-bottom-color: #4285F4; }
    .topnav .user { font-size: 12px; color: #5F6368; }
    .topnav .user a { color: #E53935 !important; margin-left: 8px; }

    /* === CARDS (Sharesight: 极细线) === */
    .card {
        background: #1A1D26; border: 1px solid #2D2D2D; border-radius: 8px;
        padding: 16px; margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }

    /* === 控制台/表单面板（分析控制台等） === */
    .pfa-control-panel {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        overflow: hidden; margin-bottom: 24px;
    }
    .pfa-control-panel .pfa-control-panel-title {
        font-size: 16px; font-weight: 600; color: #E8EAED;
        padding: 12px 16px; border-bottom: 1px solid #2D3139;
    }
    .pfa-control-panel .pfa-control-panel-body { padding: 16px; }
    /* 控制台内表单项标签统一 Caption 12px */
    .pfa-control-panel [data-testid="stSelectbox"] label,
    .pfa-control-panel [data-testid="stCheckbox"] label { font-size: 12px !important; font-weight: 500 !important; color: #5F6368 !important; }

    /* === CHAT（统一对话框边界 + 弹窗感） === */
    .expert-chat-panel {
        background: #151515;
        border: 1px solid #2D3139;
        border-radius: 16px;
        overflow: hidden;
        padding: 0;
        margin-bottom: 16px;
        box-shadow: 0 12px 32px rgba(0,0,0,0.55);
        position: relative;
        max-width: 420px;
        margin-left: auto;
    }
    .expert-chat-panel::before {
        content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
        background: #4285F4; border-radius: 16px 0 0 16px;
    }
    .expert-chat-panel .chat-panel-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 16px 14px 20px;
        border-bottom: 1px solid #2D3139;
        background: #1E1E1E;
    }
    .expert-chat-panel .chat-panel-title { font-size: 16px; font-weight: 600; color: #E8EAED; line-height: 1.4; }
    .expert-chat-panel .chat-panel-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(67,160,71,0.2); color: #43A047;
        padding: 4px 10px; border-radius: 6px;
        font-size: 12px; font-weight: 500; line-height: 1.4;
    }
    .expert-chat-panel .chat-panel-badge .dot { width: 6px; height: 6px; min-width: 6px; min-height: 6px; border-radius: 50%; background: #43A047; margin: 0; }
    .expert-chat-panel .chat-panel-desc { font-size: 12px; font-weight: 500; color: #8A8A8A; padding: 10px 16px 10px 20px; border-bottom: 1px solid #2D3139; line-height: 1.4; }
    .expert-chat-panel .chat-panel-body {
        padding: 12px 16px 8px 20px;
        background: #1A1D26;
        min-height: 220px;
    }
    /* 气泡对话：AI 左（#2B2B2B）、用户右（蓝色），Ant Design X 风格 */
    .expert-chat-panel .chat-row.chat-assistant ~ * [data-testid="stChatMessage"] {
        background: #2B2B2B !important; border: 1px solid #363636 !important;
        border-radius: 16px 16px 16px 4px !important; margin-bottom: 10px !important;
        margin-right: auto !important; margin-left: 0 !important; max-width: 90% !important;
        font-size: 14px !important; color: #E8EAED !important; line-height: 1.6 !important;
    }
    .expert-chat-panel .chat-row.chat-user ~ * [data-testid="stChatMessage"] {
        background: #1A73E8 !important; border: 1px solid #0F5FCC !important;
        border-radius: 16px 16px 4px 16px !important; margin-bottom: 10px !important;
        margin-left: auto !important; margin-right: 0 !important; max-width: 90% !important;
        font-size: 14px !important; color: #FFFFFF !important; line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] {
        background: rgba(24, 26, 32, 0.6) !important; border: 1px solid #2D3139 !important;
        border-radius: 16px !important; margin-bottom: 8px !important;
        font-size: 14px !important; font-weight: 400 !important; color: #E8EAED !important; line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] div { font-size: 14px !important; line-height: 1.6 !important; }
    .expert-chat-panel .chat-input-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
    [data-testid="stChatInput"] {
        background: #0F1116 !important;
        border-top: 1px solid #2D3139 !important;
    }
    [data-testid="stChatInput"] > div {
        background: #1A1D26 !important;
        border-radius: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: #242832 !important; color: #E8EAED !important; font-size: 14px !important; font-weight: 400 !important;
        border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #5F6368 !important; font-size: 12px !important; font-weight: 500 !important; }
    [data-testid="stChatInput"] button { background: #4285F4 !important; font-size: 14px !important; font-weight: 500 !important; }

    /* Quick actions pills inside expert chat */
    .expert-chat-panel .quick-actions-row [data-testid="baseButton-secondary"] {
        border-radius: 999px !important;
        padding: 2px 10px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        background: rgba(60,64,72,0.5) !important;
        border: 1px solid #3C4048 !important;
        color: #E8EAED !important;
        white-space: nowrap !important;
    }

    /* Dialog 右侧抽屉效果：用于投研助理等 */
    [data-testid="stDialog"] > div:first-child {
        align-items: flex-end;
    }
    [data-testid="stDialog"] [data-testid="baseDialog"] {
        width: 420px;
        max-width: 420px;
        margin-right: 0;
        margin-left: auto;
        border-radius: 16px 0 0 16px;
        animation: slideInFromRight 0.22s ease-out;
        box-shadow: 0 0 0 1px rgba(66,133,244,0.35);
    }
    @keyframes slideInFromRight {
        from { transform: translateX(24px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    /* === INPUTS（全局强制深色，禁止白底灰字） === */
    .stTextInput > div > div > input {
        background: #1A1D26 !important; color: #E8EAED !important;
        border: 1px solid #2D3139 !important; border-radius: 6px !important;
    }
    .stTextInput > div > div > input::placeholder { color: #5F6368 !important; }
    .stNumberInput > div > div > input { background: #1A1D26 !important; color: #E8EAED !important; }
    .stSelectbox > div > div { background: #1A1D26 !important; color: #E8EAED !important; }
    input, textarea {
        background: #1A1D26 !important;
        color: #E8EAED !important;
        border-color: #2D3139 !important;
    }
    input::placeholder, textarea::placeholder {
        color: #5F6368 !important;
    }

    /* === BUTTONS（深色背景 + 浅色字，禁止白底灰字） === */
    .stButton > button {
        background: #242832 !important; color: #E8EAED !important; border: 1px solid #2D3139 !important;
        border-radius: 6px; font-size: 14px; font-weight: 500; line-height: 1.4;
    }
    .stButton > button:hover { background: #2D3139 !important; border-color: #4285F4 !important; color: #E8EAED !important; }
    .stButton > button[kind="primary"] {
        background: #4285F4 !important; color: white !important; border: none !important;
        font-size: 14px !important; font-weight: 500 !important;
    }
    .stButton > button[kind="primary"]:hover { background: #3367D6 !important; }

    /* Tooltip / help / Popover：深色底 + 浅色字，禁止白底灰字 */
    [data-baseweb="popover"], [role="tooltip"], [data-baseweb="tooltip"],
    div[data-testid="stPopoverBody"], div[data-testid="stPopoverContainer"], .stPopover {
        background: #1A1D26 !important; color: #E8EAED !important;
        border: 1px solid #2D3139 !important;
    }
    [data-baseweb="popover"] span, [role="tooltip"] span, [data-baseweb="tooltip"] span,
    div[data-testid="stPopoverBody"] span, div[data-testid="stPopoverBody"] p, .stPopover * {
        color: #E8EAED !important;
    }

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] { background: transparent; }
    .stTabs [data-baseweb="tab"] { color: #9AA0A6; font-weight: 500; }
    .stTabs [aria-selected="true"] { color: #4285F4 !important; }

    /* === EXPANDER === */
    [data-testid="stExpander"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary { color: #E8EAED !important; }
    [data-testid="stExpander"] details, [data-testid="stExpander"] [data-testid="stVerticalBlock"],
    [data-testid="stExpander"] [data-testid="element-container"] {
        background: #1A1D26 !important;
    }
    [data-testid="stExpander"] p, [data-testid="stExpander"] span, [data-testid="stExpander"] div,
    [data-testid="stExpander"] label { color: #E8EAED !important; }

    /* === ALERTS（禁止白底灰字：info/warning/success/error 统一深色底+浅色字） === */
    [data-testid="stAlert"], .stAlert, div[data-baseweb="notification"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important;
        color: #E8EAED !important;
    }
    [data-testid="stAlert"] *, .stAlert *, div[data-baseweb="notification"] * {
        color: #E8EAED !important;
    }
    [data-testid="stAlert"] p, .stAlert p { color: #E8EAED !important; }
    [data-testid="stAlert"] div, .stAlert div { color: #E8EAED !important; }

    /* === BLOCK/CONTAINER（禁止白底） === */
    [data-testid="block-container"], [data-testid="stVerticalBlock"] > div,
    [data-testid="element-container"], [data-testid="column"],
    div[data-testid="stScrollableContainer"] {
        background: transparent !important;
    }
    /* 兜底：任何 inline style 白底都强制变深色，彻底消灭白底灰字 */
    [style*="background: white"], [style*="background:#fff"], [style*="background: #fff"],
    [style*="background:#F8F9FA"], [style*="background: #F8F9FA"] {
        background: #1A1D26 !important;
        color: #E8EAED !important;
    }

    /* === 设置页：卡片内列表行、摘要条、危险操作按钮 === */
    .settings-summary-strip {
        display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
        font-size: 12px; font-weight: 500; color: #5F6368; margin-bottom: 24px;
    }
    .settings-summary-strip span { color: #9AA0A6; }
    .settings-card { background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px; margin-bottom: 24px; overflow: hidden; }
    .settings-card-title { font-size: 16px; font-weight: 600; color: #E8EAED; padding: 12px 16px; border-bottom: 1px solid #2D3139; }
    .settings-card-body { padding: 16px; }
    .settings-row-cell {
        padding: 12px 0; border-bottom: 1px solid rgba(45,49,57,0.6);
        font-size: 14px; color: #E8EAED; line-height: 1.5;
    }
    .settings-row-cell:last-child { border-bottom: none; }
    .settings-row-cell .name { font-weight: 600; color: #E8EAED; margin-right: 8px; }
    .settings-row-cell .url { font-size: 12px; color: #5F6368; word-break: break-all; }
    .settings-row-cell .cat { display: inline-block; font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #242832; color: #9AA0A6; margin-left: 8px; }
    .stButton > button[kind="secondary"] { border-color: #2D3139; }
    .stButton > button.danger, button[data-danger="true"] { border-color: #E53935 !important; color: #E53935 !important; }
    .stButton > button.danger:hover { background: rgba(229,57,53,0.12) !important; }

    /* === 持仓原地编辑：透明底、仅底线的输入框，与表格同背景 === */
    .pfa-edit-table { width: 100%; background: #1A1D26; }
    .pfa-edit-table .pfa-edit-input input {
        background: transparent !important; color: #E8EAED !important;
        border: none !important; border-bottom: 1px solid #4285F4 !important; border-radius: 0 !important;
        font-size: 14px !important; font-variant-numeric: tabular-nums;
        padding: 6px 8px !important; box-shadow: none !important;
    }
    .pfa-edit-table .pfa-edit-input input:focus { border-bottom-color: #4285F4 !important; outline: none !important; }
    /* 原地编辑表：成本/数量列输入框（通过紧跟 #pfa-holdings-edit 的列定位） */
    #pfa-holdings-edit ~ div [data-testid="column"]:nth-child(5) input,
    #pfa-holdings-edit ~ div [data-testid="column"]:nth-child(6) input {
        background: transparent !important; color: #E8EAED !important;
        border: none !important; border-bottom: 1px solid #4285F4 !important; border-radius: 0 !important;
        font-size: 14px !important; font-variant-numeric: tabular-nums;
        padding: 6px 8px !important; box-shadow: none !important;
    }
    .pfa-edit-trash { font-size: 14px; cursor: pointer; padding: 4px 8px; color: #5F6368; }
    .pfa-edit-trash:hover { color: #E53935; }

    /* === 持仓编辑：仅标识「编辑中」，表格视觉与只读一致 === */
    .pfa-holdings-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .edit-mode-badge {
        display: inline-block; font-size: 12px; font-weight: 500; color: #4285F4;
        padding: 2px 8px; border: 1px solid #4285F4; border-radius: 4px;
        background: rgba(66,133,244,0.12);
    }

    /* === DATA FRAMES / DATA EDITOR（与 fin-table 一致：同背景、同字号、单元格不突出为输入框） === */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        background: #1A1D26 !important; border: 1px solid #2D3139 !important; border-radius: 8px !important;
    }
    [data-testid="stDataEditor"] [role="gridcell"] input,
    [data-testid="stDataEditor"] [role="gridcell"] select,
    [data-testid="stDataEditor"] input, [data-testid="stDataEditor"] select {
        background: #242832 !important; color: #E8EAED !important; font-size: 14px !important; font-weight: 400 !important;
        border: 1px solid #2D3139 !important; border-radius: 4px !important;
        padding: 6px 10px !important; min-height: auto !important;
    }
    [data-testid="stDataEditor"] [role="gridcell"]:focus-within input,
    [data-testid="stDataEditor"] [role="gridcell"]:focus-within select {
        border-color: #4285F4 !important; outline: none !important;
    }
    /* DataEditor 内工具栏按钮统一规范 */
    [data-testid="stDataEditor"] button, [data-testid="stDataFrame"] button {
        font-size: 14px !important; font-weight: 500 !important;
        color: #E8EAED !important; background: transparent !important; border: 1px solid #2D3139 !important;
        border-radius: 6px !important;
    }
    [data-testid="stDataEditor"] button:hover, [data-testid="stDataFrame"] button:hover {
        background: #242832 !important; border-color: #4285F4 !important;
    }

    /* === LOGIN === */
    .login-box {
        max-width: 400px; margin: 100px auto;
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 12px;
        padding: 40px; text-align: center;
    }
    .login-box .logo { font-size: 20px; font-weight: 600; color: #E8EAED; margin-bottom: 8px; }
    .login-box .sub { font-size: 12px; color: #5F6368; margin-bottom: 24px; }

    /* === EMPTY STATE === */
    .empty-state { text-align: center; padding: 48px 24px; }
    .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.6; }
    .empty-state .title { font-size: 20px; font-weight: 600; color: #E8EAED; margin-bottom: 8px; }
    .empty-state .desc { font-size: 14px; color: #5F6368; }

    /* === ONBOARDING CARDS === */
    .onboard-card {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 16px; text-align: center; cursor: pointer;
        transition: border-color 0.2s;
    }
    .onboard-card:hover { border-color: #4285F4; }
    .onboard-card .icon { font-size: 24px; margin-bottom: 8px; }
    .onboard-card .title { font-size: 14px; font-weight: 600; color: #E8EAED; }
    .onboard-card .desc { font-size: 12px; color: #5F6368; margin-top: 4px; }

    /* === CARDS (Briefing / Analysis content) === */
    .pfa-card { background: #1A1D26; border: 1px solid #2D2D2D; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.2); }
    .pfa-card .card-title { font-size: 14px; font-weight: 600; color: #E8EAED; margin-bottom: 6px; }
    .pfa-card .card-body { font-size: 14px; color: #9AA0A6; line-height: 1.5; }
    .pfa-card .card-meta { font-size: 12px; font-weight: 500; color: #5F6368; margin-top: 8px; }
    .pfa-card .badge { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
    .feed-item .title { font-size: 14px; font-weight: 600; }
    .feed-item .meta { font-size: 12px; color: #5F6368; margin-top: 4px; }

    /* === 个股概览/分析：圆点、头部、Tab、Feed 列表、情绪卡片 (NBot 参考) === */
    .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 8px; vertical-align: middle; flex-shrink: 0; }
    .dot-bullish { background: #43A047; }
    .dot-bearish { background: #E53935; }
    .dot-neutral { background: #FB8C00; }
    .dot-list { background: #E6A23C; }
    .ticker-detail-header {
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 16px 20px; margin-bottom: 16px;
    }
    .ticker-detail-header .ticker-breadcrumb { font-size: 12px; color: #9AA0A6; margin-bottom: 8px; }
    .ticker-detail-header .ticker-breadcrumb a { color: #4285F4; text-decoration: none; }
    .ticker-detail-header .ticker-breadcrumb a:hover { text-decoration: underline; }
    .ticker-detail-header .ticker-name { font-size: 20px; font-weight: 700; color: #E8EAED; margin-bottom: 2px; }
    .ticker-detail-header .ticker-fullname { font-size: 14px; color: #9AA0A6; margin-bottom: 10px; }
    .ticker-detail-header .ticker-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #9AA0A6; }
    .ticker-detail-header .price-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 600; }
    .ticker-detail-header .price-badge.up { background: rgba(67,160,71,0.2); color: #43A047; }
    .ticker-detail-header .price-badge.down { background: rgba(229,57,53,0.2); color: #E53935; }
    .ticker-tabs { display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap; }
    .ticker-tabs .tab { padding: 8px 14px; border-radius: 6px; font-size: 14px; font-weight: 500; color: #9AA0A6; cursor: pointer; text-decoration: none; }
    .ticker-tabs .tab:hover { color: #E8EAED; background: #242832; }
    .ticker-tabs .tab.active { background: #43A047; color: #fff; }
    .ticker-tabs .tab.active .dot { background: #fff; }
    .feed-list { margin-top: 12px; }
    .feed-list-item { display: flex; align-items: flex-start; gap: 10px; padding: 12px 0; border-bottom: 1px solid rgba(45,49,57,0.5); }
    .feed-list-item .feed-dot { flex-shrink: 0; width: 6px; height: 6px; border-radius: 50%; background: #E6A23C; margin-top: 6px; }
    .feed-list-item .feed-body { flex: 1; min-width: 0; }
    .feed-list-item .feed-title { font-size: 14px; font-weight: 600; color: #E8EAED; margin-bottom: 4px; line-height: 1.4; }
    .feed-list-item .feed-title a { color: #E8EAED; text-decoration: none; }
    .feed-list-item .feed-title a:hover { color: #4285F4; text-decoration: underline; }
    .feed-list-item .feed-meta { font-size: 12px; color: #5F6368; margin-bottom: 4px; }
    .feed-list-item .feed-snippet { font-size: 14px; color: #9AA0A6; line-height: 1.5; }
    .feed-list-item .feed-actions { margin-top: 8px; font-size: 12px; }
    .feed-list-item .feed-actions a { color: #4285F4; margin-right: 12px; text-decoration: none; }
    .feed-list-item .feed-actions a:hover { text-decoration: underline; }
    .feed-list-item .feed-actions span { color: #5F6368; margin-right: 12px; cursor: pointer; }
    .sentiment-score-card { background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
    .sentiment-score-card .score-num { font-size: 32px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .sentiment-score-card .score-num.bullish { color: #43A047; }
    .sentiment-score-card .score-num.bearish { color: #E53935; }
    .sentiment-bars { margin-top: 12px; }
    .sentiment-bars .bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 12px; }
    .sentiment-bars .bar-row .bar { height: 8px; border-radius: 4px; flex: 1; max-width: 120px; }
    .sentiment-bars .bar-row .bar.bullish { background: #43A047; }
    .sentiment-bars .bar-row .bar.neutral { background: #5F6368; }
    .sentiment-bars .bar-row .bar.bearish { background: #E53935; }
    .sentiment-alert { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; color: #9AA0A6; }
    .sentiment-alert .dot { margin-right: 6px; }

    /* === SENTIMENT (Briefing / Analysis) === */
    .sentiment-banner {
        display: flex; justify-content: space-between; align-items: center;
        background: #1A1D26; border: 1px solid #2D3139; border-radius: 8px;
        padding: 16px; margin-bottom: 12px;
    }
    .sentiment-banner .sentiment-label { font-size: 16px; font-weight: 600; }
    .sentiment-banner .sentiment-score { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .score-track { height: 6px; background: #2D3139; border-radius: 3px; overflow: hidden; margin-bottom: 16px; }
    .score-track .score-fill { height: 100%; border-radius: 3px; transition: width 0.2s; }

    /* === CONTAINER HEIGHT === */
    [data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
</style>""", unsafe_allow_html=True)


# Logo 主色 #4285F4（与 COLORS.brand 一致）
def _logo_data_uri():
    import base64
    # 极简乌龟图标：圆润龟壳 + 头和四肢，保持专业金融终端风格
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' fill='none'>"
        "<rect x='8' y='10' width='14' height='10' rx='5' "
        "fill='rgba(66,133,244,0.10)' stroke='#4285F4' stroke-width='1.6'/>"
        "<circle cx='23.8' cy='15' r='2.1' fill='#4285F4'/>"
        "<path d='M11 20 L9 23 M19 20 L21 23 M11 10 L9 7 M19 10 L21 7' "
        "stroke='#4285F4' stroke-width='1.4' stroke-linecap='round'/>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def render_topnav(active: str = "portfolio", user_email: str = ""):
    """Render top navigation — Sharesight 风格：细小精美，悬浮亮蓝底线。"""
    st.markdown("""<style>
    .nav-row { display: flex; align-items: center; gap: 8px; margin-bottom: 16px;
               padding: 8px 0; border-bottom: 1px solid #2D2D2D; }
    .nav-row .logo { font-size: 16px; font-weight: 600; color: #E8EAED; margin-right: 16px; }
    .nav-row .user-info { margin-left: auto; font-size: 12px; color: #5F6368; }
    .pfa-nav-logo { display: inline-flex; align-items: center; gap: 8px; }
    .pfa-nav-logo img { width: 24px; height: 24px; display: block; }
    .pfa-nav-logo .pfa-wordmark { font-size: 16px; font-weight: 600; color: #E8EAED; letter-spacing: -0.02em; }
    /* 导航链接：细小精美，悬浮亮蓝底线 */
    a[href$="pfa_dashboard.py"], a[href*="pages/"] { font-size: 12px !important; color: #9AA0A6 !important; text-decoration: none !important; border-bottom: 2px solid transparent; padding-bottom: 4px; }
    a[href$="pfa_dashboard.py"]:hover, a[href*="pages/"]:hover { color: #4285F4 !important; border-bottom-color: #4285F4; }
    </style>""", unsafe_allow_html=True)

    cols = st.columns([1, 2, 2, 2, 2, 3])
    logo_uri = _logo_data_uri()
    cols[0].markdown(
        f'<span class="pfa-nav-logo"><img src="{logo_uri}" alt="PFA" width="24" height="24"/><span class="pfa-wordmark">PFA</span></span>',
        unsafe_allow_html=True
    )

    # 注意: 这里的路径必须是「相对于主入口脚本 app/pfa_dashboard.py」，
    # 才能被 Streamlit 识别为多页应用的内部页面。
    pages = [
        ("Portfolio", "portfolio", "pfa_dashboard.py"),
        ("Briefing", "briefing", "pages/2_综合早报.py"),
        ("Analysis", "analysis", "pages/3_分析中心.py"),
        ("Settings", "settings", "pages/5_数据源配置.py"),
    ]

    for i, (label, key, page_path) in enumerate(pages):
        with cols[i + 1]:
            if key == active:
                st.markdown(f'<span style="color:#4285F4;font-weight:600;font-size:12px;border-bottom:2px solid #4285F4;padding-bottom:4px;">{label}</span>', unsafe_allow_html=True)
            else:
                try:
                    st.page_link(page_path, label=label)
                except Exception:
                    st.markdown(f'<span style="color:#9AA0A6;font-size:12px;font-weight:500;">{label}</span>', unsafe_allow_html=True)

    with cols[5]:
        if user_email:
            c1, c2 = st.columns([3, 1])
            c1.caption(user_email)
            if c2.button("退出", key="nav_logout"):
                from app.auth_v2 import _clear_token
                from pfa.data.supabase_store import sign_out, is_available
                if is_available():
                    # Supabase：通过 query 触发 get_user() 内统一清理 token + session，避免 localStorage 未清导致再次登录
                    st.query_params["logout"] = "1"
                else:
                    # 本地模式：打标后 get_user() 返回空，展示登录页
                    st.session_state["pfa_logged_out"] = True
                st.rerun()
