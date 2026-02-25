"""
PFA 投研面板 — 主入口

启动: streamlit run app/pfa_dashboard.py --server.port 8501
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="PFA 投研面板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("PFA 投研面板")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**持仓感知 · 信息降噪**\n\n"
    "基于持仓标的，从海量信息中\n筛选最值得关注的内容。"
)

st.title("PFA 投研面板")
st.markdown(
    "欢迎使用 PFA 投研面板。请从左侧导航选择功能页面：\n\n"
    "- **持仓管理** — 查看与编辑持仓标的\n"
    "- **投研看板** — 实时新闻 + 深度分析\n"
    "- **分析存档** — 按日期回溯历史分析"
)
