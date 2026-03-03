"""Auth callbacks — 登录、本地模式、登出"""

import dash
from dash import Input, Output, State
from flask import session

from pfa.data.supabase_store import is_available, sign_in


def register_auth_callbacks(app: dash.Dash):
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("login-error", "children"),
        Input("login-local", "n_clicks"),
        Input("login-submit", "n_clicks"),
        State("login-email", "value"),
        State("login-password", "value"),
        prevent_initial_call=True,
    )
    def _login(n_local, n_submit, email, password):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, ""

        triggered = ctx.triggered_id
        if triggered == "login-local":
            session["pfa_user"] = {"user_id": "admin", "email": "本地模式", "mode": "local"}
            return "/", ""

        if triggered == "login-submit" and is_available():
            if not email or not password:
                return dash.no_update, "请填写邮箱和密码"
            r = sign_in(email, password)
            if r.get("ok"):
                session["pfa_user"] = {
                    "user_id": r["user_id"],
                    "email": r.get("email", ""),
                    "access_token": r.get("access_token", ""),
                    "refresh_token": r.get("refresh_token", ""),
                    "mode": "supabase",
                }
                return "/", ""
            return dash.no_update, r.get("error", "登录失败")

        if triggered == "login-submit" and not is_available():
            return dash.no_update, "Supabase 未配置，请使用「进入本地模式」"

        return dash.no_update, ""
