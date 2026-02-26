"""
PFA v2 Auth — streamlit-local-storage 持久化

使用 streamlit-local-storage 库（同步读写浏览器 localStorage）
解决了之前 JS 注入的竞态问题。
"""

import streamlit as st
from streamlit_local_storage import LocalStorage
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out

LS_KEY = "pfa_refresh_token"


def _get_ls():
    """Lazy-init LocalStorage (must be called inside Streamlit context)."""
    if "pfa_ls" not in st.session_state:
        st.session_state["pfa_ls"] = LocalStorage()
    return st.session_state["pfa_ls"]


def _save_token(refresh_token: str):
    try:
        _get_ls().setItem(LS_KEY, refresh_token)
    except Exception:
        pass


def _read_token() -> str:
    try:
        val = _get_ls().getItem(LS_KEY)
        return val if val else ""
    except Exception:
        return ""


def _clear_token():
    try:
        _get_ls().deleteItem(LS_KEY)
    except Exception:
        pass


def get_user() -> dict:
    """Get current user. Tries: session_state → localStorage → empty."""
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # Check logout
    if st.query_params.get("logout") == "1":
        sign_out()
        st.session_state.pop("pfa_user", None)
        _clear_token()
        st.query_params.clear()
        st.rerun()

    # 1. Session state (same tab, fastest)
    s = st.session_state.get("pfa_user")
    if s and s.get("user_id"):
        return s

    # 2. Restore from localStorage (new tab / page refresh)
    rt = _read_token()
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
                    st.session_state["pfa_user"] = user_data
                    # Update token in case it rotated
                    _save_token(resp.session.refresh_token)
                    return user_data
        except Exception:
            # Token expired or invalid
            _clear_token()

    return {}


def _do_login(email: str, password: str):
    """Execute login and save session."""
    r = sign_in(email, password)
    if r.get("ok"):
        user_data = {
            "user_id": r["user_id"], "email": r["email"],
            "access_token": r.get("access_token", ""),
            "refresh_token": r.get("refresh_token", ""),
            "mode": "supabase",
        }
        st.session_state["pfa_user"] = user_data
        _save_token(r.get("refresh_token", ""))
        st.rerun()
    else:
        st.error(r.get("error", "登录失败"))


def _do_register(email: str, password: str):
    """Execute registration."""
    r = sign_up(email, password)
    if r.get("ok") and r.get("access_token"):
        user_data = {
            "user_id": r["user_id"], "email": r["email"],
            "access_token": r.get("access_token", ""),
            "refresh_token": r.get("refresh_token", ""),
            "mode": "supabase",
        }
        st.session_state["pfa_user"] = user_data
        _save_token(r.get("refresh_token", ""))
        st.success("注册成功！")
        st.rerun()
    elif r.get("needs_confirm"):
        st.success("注册成功！请检查邮箱确认后登录。")
    else:
        st.error(r.get("error", "注册失败"))


def render_login_page():
    """Render centered dark login page."""
    st.markdown("""
<div class="login-box">
    <div class="logo">PFA</div>
    <div class="sub">Portfolio Intelligence · AI-Powered</div>
</div>""", unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        tab_login, tab_reg = st.tabs(["登录", "注册"])

        with tab_login:
            email = st.text_input("邮箱", key="v2_l_email", placeholder="you@example.com")
            pwd = st.text_input("密码", type="password", key="v2_l_pwd")
            if st.button("登录", type="primary", use_container_width=True, key="v2_l_btn"):
                if email and pwd:
                    _do_login(email, pwd)

        with tab_reg:
            new_email = st.text_input("邮箱", key="v2_r_email", placeholder="you@example.com")
            new_pwd = st.text_input("密码", type="password", key="v2_r_pwd")
            new_pwd2 = st.text_input("确认密码", type="password", key="v2_r_pwd2")
            if st.button("注册", use_container_width=True, key="v2_r_btn"):
                if not new_email or not new_pwd:
                    st.error("请填写邮箱和密码")
                elif new_pwd != new_pwd2:
                    st.error("两次密码不一致")
                elif len(new_pwd) < 6:
                    st.error("密码至少 6 位")
                else:
                    _do_register(new_email, new_pwd)
