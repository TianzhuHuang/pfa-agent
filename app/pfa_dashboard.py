"""PFA 投研助手 — 主入口"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from app.theme import inject_theme, theme_toggle

st.set_page_config(page_title="PFA 投研助手", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

inject_theme()

st.sidebar.markdown("## PFA 投研助手")
theme_toggle()
st.sidebar.caption("持仓感知 · 信息降噪 · 多 Agent 协作")

st.title("PFA 投研助手")
st.markdown("""
| 页面 | 说明 |
|---|---|
| **持仓管理** | 智能搜索 / 截图识别 / 批量导入 / 多账户 |
| **综合早报** | 市场情绪 + 今日必读 + 持仓异动 |
| **分析中心** | Scout → Analyst → Auditor + 历史存档 |
| **个股深度** | 基本面 + Feed 流 + Ask Agent |
| **数据源配置** | RSS / API / RSSHub / 健康检查 |
""")
