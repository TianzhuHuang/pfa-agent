"""
PFA 助手控制中心 — 主入口

启动: streamlit run app/pfa_dashboard.py --server.port 8501
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="PFA 控制中心",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("PFA 控制中心")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**持仓感知 · 信息降噪**\n\n"
    "多 Agent 协作架构\n"
    "Scout · Analyst · Auditor · Secretary"
)

st.title("PFA 助手控制中心")
st.markdown("""
欢迎使用 PFA 投研助手。从左侧导航选择功能：

| 模块 | 功能 |
|---|---|
| **持仓管理** | 录入/编辑/批量导入持仓标的 |
| **数据源配置** | 管理 RSS、Twitter、监控 URL |
| **执行分析** | 一键触发 Scout → Analyst → Auditor |
| **分析存档** | 按日期回溯历史分析记录 |
""")
