"""
PFA v2 Auth — 居中登录页 + localStorage 持久化
"""

import streamlit as st
import streamlit.components.v1 as components
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out
from app.theme_v2 import COLORS

LS_KEY = "pfa_rt"


def _write_token(token: str):
    components.html(f"<script>localStorage.setItem('{LS_KEY}','{token}');</script>", height=0)


def _read_token_redirect():
    """On first load, check localStorage and redirect with ?_rt=token."""
    components.html(f"""<script>
    const t = localStorage.getItem('{LS_KEY}');
    if (t && !window.location.search.includes('_rt=')) {{
        const u = new URL(window.parent.location.href);
        u.searchParams.set('_rt', t);
        window.parent.location.href = u.toString();
    }}
    </script>""", height=0)


def _clear_token():
    components.html(f"""<script>
    localStorage.removeItem('{LS_KEY}');
    window.parent.location.href = '/';
    </script>""", height=0)


def get_user() -> dict:
    """Get current user or empty dict."""
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # Check logout request
    if st.query_params.get("logout") == "1":
        sign_out()
        st.session_state.pop("pfa_user", None)
        _clear_token()
        st.stop()

    # Session state
    s = st.session_state.get("pfa_user")
    if s and s.get("user_id"):
        return s

    # Restore from query param (localStorage redirect)
    rt = st.query_params.get("_rt", "")
    if rt:
        try:
            from pfa.data.supabase_store import _get_client
            client = _get_client()
            if client:
                resp = client.auth.refresh_session(rt)
                if resp.session and resp.user:
                    user = {
                        "user_id": str(resp.user.id), "email": resp.user.email,
                        "access_token": resp.session.access_token,
                        "refresh_token": resp.session.refresh_token,
                        "mode": "supabase",
                    }
                    st.session_state["pfa_user"] = user
                    _write_token(resp.session.refresh_token)
                    return user
        except Exception:
            st.query_params.pop("_rt", None)

    # Try localStorage
    _read_token_redirect()
    return {}


def render_login_page():
    """Render centered dark login page."""
    st.markdown("""
<div class="login-box">
    <div class="logo">PFA</div>
    <div class="sub">Portfolio Intelligence · AI-Powered</div>
</div>""", unsafe_allow_html=True)

    # Centered form
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        tab_login, tab_reg = st.tabs(["登录", "注册"])

        with tab_login:
            email = st.text_input("邮箱", key="v2_l_email", placeholder="you@example.com")
            pwd = st.text_input("密码", type="password", key="v2_l_pwd")
            if st.button("登录", type="primary", use_container_width=True, key="v2_l_btn"):
                if email and pwd:
                    r = sign_in(email, pwd)
                    if r.get("ok"):
                        user = {
                            "user_id": r["user_id"], "email": r["email"],
                            "access_token": r.get("access_token", ""),
                            "refresh_token": r.get("refresh_token", ""),
                            "mode": "supabase",
                        }
                        st.session_state["pfa_user"] = user
                        _write_token(r.get("refresh_token", ""))
                        st.rerun()
                    else:
                        st.error(r.get("error", "登录失败"))

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
                    r = sign_up(new_email, new_pwd)
                    if r.get("ok") and r.get("access_token"):
                        user = {
                            "user_id": r["user_id"], "email": r["email"],
                            "access_token": r.get("access_token", ""),
                            "refresh_token": r.get("refresh_token", ""),
                            "mode": "supabase",
                        }
                        st.session_state["pfa_user"] = user
                        _write_token(r.get("refresh_token", ""))
                        st.success("注册成功！")
                        st.rerun()
                    elif r.get("needs_confirm"):
                        st.success("注册成功！请检查邮箱确认后登录。")
                    else:
                        st.error(r.get("error", "注册失败"))
