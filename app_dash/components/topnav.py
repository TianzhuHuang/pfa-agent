"""Top navigation component — Stake 风格"""

import dash.html as html
import dash.dcc as dcc
from pfa.theme_utils import logo_data_uri


def topnav(active: str = "portfolio", user_email: str = "") -> html.Div:
    links = [
        ("/", "Portfolio", "portfolio"),
        ("/briefing", "Briefing", "briefing"),
        ("/analysis", "Analysis", "analysis"),
        ("/settings", "Settings", "settings"),
    ]
    logo_uri = logo_data_uri()
    return html.Div(
        className="pfa-topnav",
        children=[
            html.A(
                href="/",
                className="logo",
                children=[
                    html.Img(src=logo_uri, alt="PFA", width=24, height=24),
                    html.Span("PFA"),
                ],
            ),
            html.Div(
                className="nav-links",
                children=[
                    html.A(label, href=path, className="active" if active == key else "")
                    for path, label, key in links
                ],
            ),
            html.Div(
                className="user-info",
                children=[
                    html.Span(user_email or "已登录", style={"marginRight": "12px"}),
                    html.A("退出", href="/logout", style={"fontSize": "12px", "color": "#9AA0A6"}),
                ],
            ),
        ],
    )
