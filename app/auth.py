"""
PFA 登录/注册组件 — Cookie 持久化 + Supabase Auth
"""

import streamlit as st
import extra_streamlit_components as stx
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out

COOKIE_KEY = "pfa_refresh_token"


def _get_cookie_manager():
    return stx.CookieManager(key="pfa_cookies")


def _save_session(user_data: dict):
    """Save session to session_state + cookie."""
    st.session_state["pfa_user"] = user_data
    try:
        cm = _get_cookie_manager()
        if user_data.get("refresh_token"):
            cm.set(COOKIE_KEY, user_data["refresh_token"],
                   key="set_cookie", max_age=30*24*3600)  # 30 days
    except Exception:
        pass


def get_user() -> dict:
    """Get current user. Tries: session_state → cookie → empty."""
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # 1. Check session_state
    session = st.session_state.get("pfa_user")
    if session and session.get("user_id"):
        return session

    # 2. Try restore from cookie
    try:
        cm = _get_cookie_manager()
        rt = cm.get(COOKIE_KEY)
        if rt:
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
                    st.session_state["pfa_user"] = user_data
                    return user_data
    except Exception:
        pass

    return {}


def render_auth_sidebar():
    """Render login/register in sidebar."""
    user = get_user()

    if user.get("mode") == "local":
        st.sidebar.caption("📦 本地模式")
        return user

    if user.get("user_id"):
        st.sidebar.markdown(f"👤 **{user['email']}**")
        if st.sidebar.button("退出", use_container_width=True):
            sign_out()
            st.session_state.pop("pfa_user", None)
            try:
                cm = _get_cookie_manager()
                cm.delete(COOKIE_KEY, key="del_cookie")
            except Exception:
                pass
            st.rerun()
        return user

    # Login/Register
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
