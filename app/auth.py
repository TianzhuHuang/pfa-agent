"""
PFA 登录/注册 — localStorage 持久化（最可靠方案）

原理: 通过 st.components.v1.html 注入 JS，读写浏览器 localStorage。
关闭标签页后重新打开，从 localStorage 恢复 refresh_token → 自动登录。
"""

import json
import streamlit as st
import streamlit.components.v1 as components
from pfa.data.supabase_store import is_available, sign_in, sign_up, sign_out

LS_KEY = "pfa_rt"


def _write_token_to_browser(token: str):
    """Inject JS to save refresh_token to localStorage."""
    components.html(f"""
    <script>
        localStorage.setItem('{LS_KEY}', '{token}');
        // Signal back to Streamlit that token is saved
        window.parent.postMessage({{type: 'pfa_token_saved'}}, '*');
    </script>
    """, height=0)


def _read_token_from_browser():
    """Inject JS to read refresh_token from localStorage and pass it back via query param."""
    # We use a two-step approach:
    # 1. On first load, inject JS that reads localStorage and redirects with ?_rt=xxx
    # 2. On redirect, Python reads the query param
    params = st.query_params
    rt = params.get("_rt", "")
    if rt:
        return rt

    # Inject JS to check localStorage and redirect if token exists
    components.html(f"""
    <script>
        const token = localStorage.getItem('{LS_KEY}');
        if (token && !window.location.search.includes('_rt=')) {{
            // Append token to URL and reload
            const url = new URL(window.parent.location.href);
            url.searchParams.set('_rt', token);
            window.parent.location.href = url.toString();
        }}
    </script>
    """, height=0)
    return ""


def _clear_token_from_browser():
    """Inject JS to remove refresh_token from localStorage."""
    components.html(f"""
    <script>
        localStorage.removeItem('{LS_KEY}');
        const url = new URL(window.parent.location.href);
        url.searchParams.delete('_rt');
        window.parent.location.href = url.toString();
    </script>
    """, height=0)


def _save_session(user_data: dict):
    st.session_state["pfa_user"] = user_data
    if user_data.get("refresh_token"):
        _write_token_to_browser(user_data["refresh_token"])


def get_user() -> dict:
    if not is_available():
        return {"user_id": "admin", "email": "本地模式", "mode": "local"}

    # 1. Check session_state (same tab)
    session = st.session_state.get("pfa_user")
    if session and session.get("user_id"):
        return session

    # 2. Check query param (from localStorage redirect)
    rt = st.query_params.get("_rt", "")
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
                    # Update localStorage with new token
                    _write_token_to_browser(resp.session.refresh_token)
                    return user_data
        except Exception:
            # Token expired — clear it
            st.query_params.pop("_rt", None)

    # 3. Try to read from localStorage (first visit, no _rt param yet)
    _read_token_from_browser()

    return {}


def render_auth_sidebar():
    user = get_user()

    if user.get("mode") == "local":
        st.sidebar.caption("📦 本地模式")
        return user

    if user.get("user_id"):
        st.sidebar.markdown(f"👤 **{user['email']}**")
        if st.sidebar.button("退出", use_container_width=True):
            sign_out()
            st.session_state.pop("pfa_user", None)
            _clear_token_from_browser()
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
