"""
PFA 登录/注册组件 — Streamlit 侧边栏集成

检测 Supabase 可用性：
  - 有 Supabase → 显示登录/注册
  - 无 Supabase → 自动以 admin 身份运行（本地模式）
"""

import streamlit as st
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out


def get_user() -> dict:
    """Get current user info. Returns {user_id, email, mode}.

    mode: 'supabase' (cloud login) or 'local' (no auth, admin)
    """
    if not is_available():
        return {"user_id": "admin", "email": "local", "mode": "local"}

    session = st.session_state.get("pfa_user")
    if session and session.get("user_id"):
        return session
    return {}


def render_auth_sidebar():
    """Render login/register UI in sidebar. Returns user dict or empty."""
    user = get_user()

    if user.get("mode") == "local":
        st.sidebar.caption("📦 本地模式 (无需登录)")
        return user

    if user.get("user_id"):
        st.sidebar.markdown(f"👤 **{user['email']}**")
        if st.sidebar.button("退出登录", use_container_width=True):
            sign_out()
            st.session_state.pop("pfa_user", None)
            st.rerun()
        return user

    # Not logged in — show login form
    st.sidebar.markdown("### 🔐 登录")

    tab_login, tab_register = st.sidebar.tabs(["登录", "注册"])

    with tab_login:
        email = st.text_input("邮箱", key="login_email")
        password = st.text_input("密码", type="password", key="login_pwd")
        if st.button("登录", type="primary", use_container_width=True, key="btn_login"):
            if email and password:
                result = sign_in(email, password)
                if result.get("ok"):
                    st.session_state["pfa_user"] = {
                        "user_id": result["user_id"],
                        "email": result["email"],
                        "access_token": result.get("access_token", ""),
                        "mode": "supabase",
                    }
                    st.success(f"欢迎回来！")
                    st.rerun()
                else:
                    st.error(result.get("error", "登录失败"))

    with tab_register:
        new_email = st.text_input("邮箱", key="reg_email")
        new_pwd = st.text_input("密码", type="password", key="reg_pwd")
        new_pwd2 = st.text_input("确认密码", type="password", key="reg_pwd2")
        if st.button("注册", use_container_width=True, key="btn_reg"):
            if not new_email or not new_pwd:
                st.error("请填写邮箱和密码")
            elif new_pwd != new_pwd2:
                st.error("两次密码不一致")
            elif len(new_pwd) < 6:
                st.error("密码至少 6 位")
            else:
                result = sign_up(new_email, new_pwd)
                if result.get("ok"):
                    st.success("注册成功！请检查邮箱确认后登录。")
                else:
                    st.error(result.get("error", "注册失败"))

    return {}
