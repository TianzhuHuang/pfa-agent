"""
PFA Dash 应用入口

运行: dash run app_dash.app:app
或: python -m dash run app_dash.app:app
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dash
from dash import Input, Output
from flask import session

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _get_holdings_val():
    """Get portfolio valuation for chat context."""
    try:
        from agents.secretary_agent import load_portfolio
        from pfa.portfolio_valuation import calculate_portfolio_value
        p = load_portfolio()
        holdings = p.get("holdings", [])
        return calculate_portfolio_value(holdings) if holdings else {}
    except Exception:
        return {}


# Create Dash app
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder="assets",
    title="PFA",
    update_title="",  # 禁用回调时标签页显示 "Updating..." 的闪烁
)
app.config.suppress_callback_exceptions = True

# Flask session secret (required for session)
if not app.server.secret_key:
    app.server.secret_key = os.environ.get("FLASK_SECRET_KEY", "pfa-dash-dev-secret-change-in-prod")


@app.server.before_request
def _handle_logout():
    from flask import request, session, redirect
    if request.path == "/logout":
        session.pop("pfa_user", None)
        return redirect("/")

# Register callbacks
from app_dash.callbacks.auth import register_auth_callbacks
from app_dash.callbacks.chat import register_chat_callbacks
from app_dash.callbacks.entry_modal import register_entry_modal_callbacks
from app_dash.callbacks.briefing import register_briefing_callbacks
from app_dash.callbacks.analysis import register_analysis_callbacks
from app_dash.callbacks.settings import register_settings_callbacks

register_auth_callbacks(app)
register_chat_callbacks(app, _get_holdings_val)
register_entry_modal_callbacks(app)
register_briefing_callbacks(app)
register_analysis_callbacks(app)
register_settings_callbacks(app)

# Layout: URL-driven page content
from app_dash.layout import get_layout

app.layout = dash.html.Div(
    id="root",
    children=[
        dash.dcc.Location(id="url", refresh=False),
        dash.html.Div(id="page-content"),
    ],
    style={"minHeight": "100vh", "background": "#0f212e"},
)


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def _display_page(pathname):
    pathname = pathname or "/"
    return get_layout(pathname, _get_holdings_val)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
