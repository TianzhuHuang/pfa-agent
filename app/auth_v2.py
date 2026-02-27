"""
PFA v2 Auth — Supabase session + cookie persistence

Uses multiple fallback layers for login persistence:
1. st.session_state (same tab)
2. streamlit-local-storage (across tabs/refreshes)  
3. Supabase auto-refresh (if token exists)
"""

import streamlit as st
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out

LS_KEY = "pfa_refresh_token"


def _get_ls():
    """Lazy-init LocalStorage."""
    try:
        from streamlit_local_storage import LocalStorage
        if "pfa_ls" not in st.session_state:
            st.session_state["pfa_ls"] = LocalStorage()
        return st.session_state["pfa_ls"]
    except Exception:
        return None


def _save_token(token: str):
    ls = _get_ls()
    if ls:
        try:
            ls.setItem(LS_KEY, token)
        except Exception:
            pass


def _read_token() -> str:
    ls = _get_ls()
    if ls:
        try:
            v = ls.getItem(LS_KEY)
            return v if v else ""
        except Exception:
            pass
    return ""


def _clear_token():
    ls = _get_ls()
    if ls:
        try:
            ls.deleteItem(LS_KEY)
        except Exception:
            pass


def get_user() -> dict:
    """Get current user from session or localStorage."""
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # Handle logout
    if st.query_params.get("logout") == "1":
        sign_out()
        st.session_state.pop("pfa_user", None)
        _clear_token()
        st.query_params.clear()
        st.rerun()

    # 1. Session state (fastest, same page session)
    s = st.session_state.get("pfa_user")
    if s and s.get("user_id"):
        return s

    # 2. Try localStorage token
    rt = _read_token()
    if rt:
        try:
            from pfa.data.supabase_store import _get_client
            client = _get_client()
            if client:
                resp = client.auth.refresh_session(rt)
                if resp.session and resp.user:
                    ud = {
                        "user_id": str(resp.user.id),
                        "email": resp.user.email,
                        "access_token": resp.session.access_token,
                        "refresh_token": resp.session.refresh_token,
                        "mode": "supabase",
                    }
                    st.session_state["pfa_user"] = ud
                    _save_token(resp.session.refresh_token)
                    return ud
        except Exception:
            _clear_token()

    return {}


def render_login_page():
    """Centered dark login page."""
    st.markdown("""
<div class="login-box">
    <div class="logo">PFA</div>
    <div class="sub">Portfolio Intelligence · AI-Powered</div>
</div>""", unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        tab_login, tab_reg = st.tabs(["登录", "注册"])

        with tab_login:
            email = st.text_input("邮箱", key="l_e", placeholder="you@example.com")
            pwd = st.text_input("密码", type="password", key="l_p")
            if st.button("登录", type="primary", use_container_width=True, key="l_b"):
                if email and pwd:
                    r = sign_in(email, pwd)
                    if r.get("ok"):
                        ud = {
                            "user_id": r["user_id"], "email": r["email"],
                            "access_token": r.get("access_token", ""),
                            "refresh_token": r.get("refresh_token", ""),
                            "mode": "supabase",
                        }
                        st.session_state["pfa_user"] = ud
                        _save_token(r.get("refresh_token", ""))
                        st.rerun()
                    else:
                        st.error(r.get("error", "登录失败"))

        with tab_reg:
            ne = st.text_input("邮箱", key="r_e", placeholder="you@example.com")
            np = st.text_input("密码", type="password", key="r_p")
            np2 = st.text_input("确认密码", type="password", key="r_p2")
            if st.button("注册", use_container_width=True, key="r_b"):
                if not ne or not np:
                    st.error("请填写邮箱和密码")
                elif np != np2:
                    st.error("两次密码不一致")
                elif len(np) < 6:
                    st.error("密码至少 6 位")
                else:
                    r = sign_up(ne, np)
                    if r.get("ok") and r.get("access_token"):
                        ud = {
                            "user_id": r["user_id"], "email": r["email"],
                            "access_token": r.get("access_token", ""),
                            "refresh_token": r.get("refresh_token", ""),
                            "mode": "supabase",
                        }
                        st.session_state["pfa_user"] = ud
                        _save_token(r.get("refresh_token", ""))
                        st.success("注册成功！")
                        st.rerun()
                    elif r.get("needs_confirm"):
                        st.success("注册成功！请检查邮箱确认后登录。")
                    else:
                        st.error(r.get("error", "注册失败"))
