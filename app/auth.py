"""
PFA 登录/注册组件 — Session 持久化 + 自动检测模式
"""

import streamlit as st
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out


def _save_session(user_data: dict):
    """Save session to session_state + query_params (survives reload)."""
    st.session_state["pfa_user"] = user_data
    if user_data.get("refresh_token"):
        st.query_params["_rt"] = user_data["refresh_token"]


def get_user() -> dict:
    """Get current user. Returns {user_id, email, mode} or empty.

    Persistence: stores refresh_token in query_params so login survives
    page reloads and tab closes (as long as the URL is preserved).
    """
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # Check session_state first
    session = st.session_state.get("pfa_user")
    if session and session.get("user_id"):
        return session

    # Try to restore session from query_params (survives page reload)
    params = st.query_params
    rt = params.get("_rt", "")
    if rt:
        try:
            from pfa.data.supabase_store import _get_client
            client = _get_client()
            if client:
                resp = client.auth.refresh_session(rt)
                if resp.session and resp.user:
                    user_data = {
                        "user_id": str(resp.user.id),
                        "email": resp.user.email,
                        "access_token": resp.session.access_token,
                        "refresh_token": resp.session.refresh_token,
                        "mode": "supabase",
                    }
                    _save_session(user_data)
                    return user_data
        except Exception:
            # Token expired, clear it
            st.query_params.pop("_rt", None)

    return {}


def render_auth_sidebar():
    """Render login/register in sidebar. Returns user dict."""
    user = get_user()

    if user.get("mode") == "local":
        st.sidebar.caption("📦 本地模式")
        return user

    if user.get("user_id"):
        st.sidebar.markdown(f"👤 **{user['email']}**")
        if st.sidebar.button("退出", use_container_width=True):
            sign_out()
            st.session_state.pop("pfa_user", None)
            st.query_params.pop("_rt", None)
            st.rerun()
        return user

    # Login/Register form
    st.sidebar.markdown("### 🔐 登录")

    tab_login, tab_reg = st.sidebar.tabs(["登录", "注册"])

    with tab_login:
        email = st.text_input("邮箱", key="l_email")
        pwd = st.text_input("密码", type="password", key="l_pwd")
        if st.button("登录", type="primary", use_container_width=True, key="l_btn"):
            if email and pwd:
                r = sign_in(email, pwd)
                if r.get("ok"):
                    _save_session({
                        "user_id": r["user_id"], "email": r["email"],
                        "access_token": r.get("access_token", ""),
                        "refresh_token": r.get("refresh_token", ""),
                        "mode": "supabase",
                    })
                    st.rerun()
                else:
                    st.error(r.get("error", "登录失败"))

    with tab_reg:
        new_email = st.text_input("邮箱", key="r_email")
        new_pwd = st.text_input("密码", type="password", key="r_pwd")
        new_pwd2 = st.text_input("确认密码", type="password", key="r_pwd2")
        if st.button("注册", use_container_width=True, key="r_btn"):
            if not new_email or not new_pwd:
                st.error("请填写邮箱和密码")
            elif new_pwd != new_pwd2:
                st.error("两次密码不一致")
            elif len(new_pwd) < 6:
                st.error("密码至少 6 位")
            else:
                r = sign_up(new_email, new_pwd)
                if r.get("ok") and r.get("access_token"):
                    _save_session({
                        "user_id": r["user_id"], "email": r["email"],
                        "access_token": r.get("access_token", ""),
                        "refresh_token": r.get("refresh_token", ""),
                        "mode": "supabase",
                    })
                    st.success("注册成功！")
                    st.rerun()
                elif r.get("ok") and r.get("needs_confirm"):
                    st.success("注册成功！请检查邮箱确认后登录。")
                else:
                    st.error(r.get("error", "注册失败"))

    return {}
