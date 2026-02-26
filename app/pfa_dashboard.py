"""PFA 投研助手 — 主入口 (st.navigation 控制侧栏)"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="PFA 投研助手", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

from app.theme import inject_theme, theme_toggle
from app.auth import render_auth_sidebar

inject_theme()

st.sidebar.markdown("## PFA 投研助手")
user = render_auth_sidebar()
theme_toggle()
st.sidebar.caption("持仓感知 · 信息降噪 · 多 Agent 协作")

if not user.get("user_id"):
    st.title("PFA 投研助手")
    st.info("请在左侧登录或注册以开始使用。")
    st.stop()

# Check if we should show ticker detail (via query param)
params = st.query_params
if params.get("page") == "ticker" and params.get("symbol"):
    # Inline render ticker detail
    exec(open(str(ROOT / "app" / "ticker_detail.py")).read())
else:
    mode_badge = "☁️ 云端" if user.get("mode") == "supabase" else "📦 本地"
    st.title("PFA 投研助手")
    st.caption(f"{mode_badge} · {user.get('email', '')}")
    st.markdown("""
| 页面 | 说明 |
|---|---|
| **持仓管理** | 智能搜索 / 截图识别 / 批量导入 / 多账户 |
| **综合早报** | 市场情绪 + 今日必读 + 持仓异动 |
| **分析中心** | Scout → Analyst → Auditor + 历史存档 |
| **数据源配置** | RSS / API / RSSHub / 健康检查 |

*点击持仓表中的股票代码可查看个股深度分析*
""")
