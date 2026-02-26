"""
PFA 全局主题 — NBOT 风格暗色/亮色切换 + 卡片组件
"""

import streamlit as st

# A-share convention: red = bullish, green = bearish (opposite of US)
COLORS = {
    "bullish": "#e74c3c",       # 红涨
    "bearish": "#27ae60",       # 绿跌
    "neutral": "#7f8c8d",
    "accent": "#c8ff00",        # NBOT 荧光绿
    "bg_dark": "#0a0a0a",
    "bg_card_dark": "#1a1a1a",
    "bg_light": "#ffffff",
    "bg_card_light": "#f8f9fa",
    "text_dark": "#e0e0e0",
    "text_light": "#1a1a1a",
    "border_dark": "#2a2a2a",
    "border_light": "#e0e0e0",
    "positive": "#e74c3c",      # A股红涨
    "negative": "#27ae60",      # A股绿跌
}


def inject_theme():
    """Inject global CSS based on theme toggle."""
    dark = st.session_state.get("dark_mode", True)

    bg = COLORS["bg_dark"] if dark else COLORS["bg_light"]
    card_bg = COLORS["bg_card_dark"] if dark else COLORS["bg_card_light"]
    text = COLORS["text_dark"] if dark else COLORS["text_light"]
    border = COLORS["border_dark"] if dark else COLORS["border_light"]
    sub_text = "#999" if dark else "#666"

    st.markdown(f"""<style>
    /* Global */
    .stApp {{ background-color: {bg}; color: {text}; }}
    .stMarkdown, .stText, p, li, span {{ color: {text}; }}
    h1, h2, h3, h4 {{ color: {text}; font-family: -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif; }}
    h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
    h2 {{ font-size: 22px; font-weight: 600; }}
    h3 {{ font-size: 17px; font-weight: 600; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{ background-color: {'#111' if dark else '#f0f2f6'}; }}
    [data-testid="stSidebar"] * {{ color: {text}; }}

    /* Cards */
    .pfa-card {{
        background: {card_bg}; border: 1px solid {border};
        border-radius: 10px; padding: 16px; margin-bottom: 12px;
        transition: box-shadow 0.2s;
    }}
    .pfa-card:hover {{ box-shadow: 0 2px 12px rgba(0,0,0,{'0.3' if dark else '0.08'}); }}
    .pfa-card .card-title {{ font-size: 15px; font-weight: 600; color: {text}; margin-bottom: 6px; }}
    .pfa-card .card-body {{ font-size: 13px; color: {sub_text}; line-height: 1.6; }}
    .pfa-card .card-meta {{ font-size: 11px; color: {'#666' if dark else '#999'}; margin-top: 8px; }}

    /* Priority borders */
    .pfa-card.high {{ border-left: 4px solid {COLORS['bullish']}; }}
    .pfa-card.medium {{ border-left: 4px solid #f39c12; }}
    .pfa-card.low {{ border-left: 4px solid {COLORS['neutral']}; }}
    .pfa-card.positive {{ border-left: 4px solid {COLORS['positive']}; }}
    .pfa-card.negative {{ border-left: 4px solid {COLORS['negative']}; }}

    /* Badges */
    .badge {{
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 11px; font-weight: 600;
    }}
    .badge-positive {{ background: rgba(231,76,60,0.15); color: {COLORS['positive']}; }}
    .badge-negative {{ background: rgba(39,174,96,0.15); color: {COLORS['negative']}; }}
    .badge-neutral {{ background: rgba(127,140,141,0.15); color: {COLORS['neutral']}; }}

    /* Sentiment banner */
    .sentiment-banner {{
        background: {card_bg}; border: 1px solid {border};
        border-radius: 12px; padding: 20px 24px;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 20px;
    }}
    .sentiment-score {{ font-size: 36px; font-weight: 800; }}
    .sentiment-label {{ font-size: 20px; font-weight: 700; }}

    /* Score bar */
    .score-track {{
        height: 6px; border-radius: 3px; background: {border};
        margin: 8px 0; overflow: hidden;
    }}
    .score-fill {{ height: 100%; border-radius: 3px; }}

    /* Move card grid */
    .move-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    @media (max-width: 768px) {{ .move-grid {{ grid-template-columns: 1fr; }} }}

    /* Feed item */
    .feed-item {{
        padding: 12px 0; border-bottom: 1px solid {border};
    }}
    .feed-item:last-child {{ border-bottom: none; }}
    .feed-item .title {{ font-size: 14px; font-weight: 600; color: {text}; }}
    .feed-item .title a {{ color: {text}; text-decoration: none; }}
    .feed-item .title a:hover {{ color: {COLORS['accent'] if dark else COLORS['bullish']}; }}
    .feed-item .snippet {{ font-size: 12px; color: {sub_text}; margin-top: 4px; }}
    .feed-item .meta {{ font-size: 11px; color: {'#555' if dark else '#aaa'}; margin-top: 4px; }}

    /* Data tables — unified dark/light */
    .stDataFrame, [data-testid="stDataFrame"],
    [data-testid="stDataFrameResizable"],
    [data-testid="stDataFrame"] > div,
    .stDataFrame iframe {{ background: {card_bg} !important; }}
    [data-testid="stDataFrameResizable"] {{ border: 1px solid {border} !important; border-radius: 8px !important; overflow: hidden; }}
    /* Glide data grid (internal table renderer) */
    [data-testid="stDataFrame"] canvas + div {{ background: {card_bg} !important; }}
    [data-testid="stDataFrame"] [role="grid"] {{ background: {card_bg} !important; }}
    [data-testid="stDataFrame"] [data-testid="glideDataEditor"] {{ background: {card_bg} !important; }}

    /* Data editor */
    [data-testid="stDataEditor"] {{ background: {card_bg} !important; border: 1px solid {border} !important; border-radius: 8px !important; }}
    [data-testid="stDataEditor"] [role="grid"] {{ background: {card_bg} !important; }}

    /* Expander */
    [data-testid="stExpander"] {{ background: {card_bg}; border: 1px solid {border}; border-radius: 8px; }}
    [data-testid="stExpander"] summary {{ color: {text}; }}

    /* Select / Input */
    .stSelectbox > div > div {{ background: {card_bg} !important; color: {text} !important; }}
    .stTextInput > div > div > input {{ background: {card_bg} !important; color: {text} !important; border-color: {border} !important; }}
    .stNumberInput > div > div > input {{ background: {card_bg} !important; color: {text} !important; }}

    /* Metric */
    [data-testid="stMetricValue"] {{ color: {text} !important; }}

    /* Chat */
    [data-testid="stChatMessage"] {{ background: {card_bg} !important; border: 1px solid {border}; border-radius: 10px; margin-bottom: 8px; }}
    [data-testid="stChatInput"] {{ border-color: {border} !important; }}
    [data-testid="stChatInput"] textarea {{ background: {card_bg} !important; color: {text} !important; }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ background: transparent; }}
    .stTabs [data-baseweb="tab"] {{ color: {sub_text}; }}
    .stTabs [aria-selected="true"] {{ color: {COLORS['accent'] if dark else COLORS['bullish']}; }}

    /* Buttons */
    .stButton > button {{ border-color: {border}; }}
    </style>""", unsafe_allow_html=True)


def theme_toggle():
    """Render theme toggle in sidebar."""
    dark = st.session_state.get("dark_mode", True)
    label = "☀️ 亮色" if dark else "🌙 暗色"
    if st.sidebar.button(label, use_container_width=True):
        st.session_state["dark_mode"] = not dark
        st.rerun()


def render_card(title: str, body: str, meta: str = "",
                priority: str = "", sentiment: str = "",
                url: str = "") -> str:
    """Return HTML for a styled card."""
    from html import escape
    cls = priority or sentiment
    title_html = f'<a href="{escape(url)}" target="_blank">{escape(title)}</a>' if url else escape(title)
    badge = ""
    if sentiment:
        badge = f' <span class="badge badge-{escape(sentiment)}">{escape(sentiment)}</span>'
    return f"""<div class="pfa-card {escape(cls)}">
    <div class="card-title">{title_html}{badge}</div>
    <div class="card-body">{escape(body)}</div>
    <div class="card-meta">{escape(meta)}</div>
</div>"""
