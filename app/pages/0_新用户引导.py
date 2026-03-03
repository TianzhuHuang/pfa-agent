"""
占位页：引导页已移除，自动跳转至 Portfolio 主页面。
"""
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.theme_v2 import inject_v2_theme, render_topnav
from app.auth_v2 import get_user, render_login_page

st.set_page_config(page_title="PFA", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
inject_v2_theme()

user = get_user()
if not user.get("user_id"):
    render_login_page()
    st.stop()

render_topnav(active="guide", user_email=user.get("email") or ("已登录" if user.get("user_id") else ""))

# 自动跳转：若 switch_page 失败，显示可点击链接
try:
    st.switch_page("pfa_dashboard.py")
except Exception:
    pass

# 若未跳转，显示返回入口
st.markdown(
    """
<div class="pfa-card" style="text-align:center; padding:48px 24px;">
  <div style="font-size:32px; margin-bottom:16px;">📊</div>
  <div class="pfa-title" style="margin-bottom:12px;">正在返回持仓大屏</div>
  <div class="pfa-body" style="color:#9AA0A6; margin-bottom:20px;">
    引导页已合并至主页面，请点击下方按钮返回。
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.page_link("pfa_dashboard.py", label="返回 Portfolio", icon="📊")
