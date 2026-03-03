"""Root layout — 顶栏、主区、路由"""

import dash.html as html
import dash.dcc as dcc
from flask import session

from app_dash.components.topnav import topnav
from app_dash.components.chat import chat_component
from pfa.data.store import load_chat_history
from pfa.ai_chat import build_welcome_message


def get_user():
    """Get current user from flask session."""
    return session.get("pfa_user", {})


def get_layout(pathname: str, get_holdings_val_fn):
    """Build layout for given pathname."""
    user = get_user()
    user_id = user.get("user_id") or "admin"
    user_email = user.get("email") or ""

    # Login required for all pages except /login
    if pathname == "/login" or pathname == "/login/":
        from app_dash.pages.login import login_page
        return login_page()

    if not user.get("user_id"):
        from app_dash.pages.login import login_page
        return login_page()

    # Load chat history for portfolio page
    chat_initial = []
    if pathname == "/" or pathname == "/portfolio" or not pathname:
        stored = load_chat_history(user_id)
        if stored:
            chat_initial = stored
        else:
            val = {}
            if get_holdings_val_fn:
                try:
                    val = get_holdings_val_fn()
                except Exception:
                    pass
            welcome = build_welcome_message(val) if val else "👋 你好，我是你的 AI 投研助理。"
            chat_initial = [{"role": "assistant", "content": welcome}]

    active = "portfolio"
    if pathname and pathname.startswith("/briefing"):
        active = "briefing"
    elif pathname and pathname.startswith("/analysis"):
        active = "analysis"
    elif pathname and pathname.startswith("/settings"):
        active = "settings"

    nav = topnav(active=active, user_email=user_email)

    # Portfolio: full page with holdings + chat
    if pathname == "/" or pathname == "/portfolio" or not pathname:
        from app_dash.pages.portfolio import portfolio_page
        holdings = []
        val = {"total_value_cny": 0, "total_pnl_cny": 0, "total_pnl_pct": 0, "holding_count": 0, "account_count": 0, "by_account": {}}
        try:
            from agents.secretary_agent import load_portfolio
            from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
            p = load_portfolio()
            holdings = p.get("holdings", [])
            if holdings:
                fx = get_fx_rates()
                prices = get_realtime_prices(holdings)
                val = calculate_portfolio_value(holdings, prices, fx)
        except Exception:
            pass
        content = portfolio_page(holdings=holdings, val=val, chat_initial=chat_initial, user_id=user_id)
    elif pathname and pathname.startswith("/briefing"):
        from app_dash.pages.briefing import briefing_page
        content = briefing_page()
    elif pathname and pathname.startswith("/analysis"):
        from app_dash.pages.analysis import analysis_page
        holdings_a, val_a = [], {"total_value_cny": 0, "by_account": {}}
        try:
            from agents.secretary_agent import load_portfolio
            from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
            p = load_portfolio()
            holdings_a = p.get("holdings", [])
            if holdings_a:
                fx = get_fx_rates()
                prices = get_realtime_prices(holdings_a)
                val_a = calculate_portfolio_value(holdings_a, prices, fx)
        except Exception:
            pass
        chat_initial_a = load_chat_history(user_id) or [{"role": "assistant", "content": build_welcome_message(val_a) if val_a.get("holding_count") else "👋 你好，我是你的 AI 投研助理。"}]
        content = analysis_page(holdings=holdings_a, val=val_a, chat_initial=chat_initial_a, user_id=user_id)
    elif pathname and pathname.startswith("/settings"):
        from app_dash.pages.settings import settings_page
        content = settings_page()
    else:
        content = html.Div(
            className="main-content",
            children=[html.P(f"Page: {pathname}", style={"color": "#9AA0A6"})],
        )

    return html.Div(
        style={"display": "flex", "flexDirection": "column", "minHeight": "100vh", "background": "#0f212e"},
        children=[nav, content],
    )
