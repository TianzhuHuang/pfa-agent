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
    page_title="PFA 投研助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.markdown("## PFA 投研助手")
st.sidebar.caption("持仓感知 · 信息降噪 · 多 Agent 协作")

st.title("PFA 投研助手")
st.markdown("""
| 页面 | 说明 |
|---|---|
| **持仓管理** | 智能搜索 / 截图识别 / 批量导入 / 多账户 |
| **综合早报** | 每日市场情绪 + 持仓关键事件 + AI 摘要 |
| **分析中心** | 一键 Scout→Analyst→Auditor + 历史存档 |
| **个股深度** | 个股信息流 + AI 观点 + 交互问答 |
| **数据源配置** | RSS / API / RSSHub 管理 |
""")
