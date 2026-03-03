"""Login page — 深色主题"""

import dash.html as html
import dash.dcc as dcc
from pfa.theme_utils import logo_data_uri


def login_page() -> html.Div:
    logo_uri = logo_data_uri()
    return html.Div(
        className="login-container",
        children=[
            html.Div(
                className="login-box",
                children=[
                    html.Div(
                        className="logo",
                        children=[
                            html.Img(src=logo_uri, alt="PFA", width=48, height=48),
                            html.Span("PFA"),
                        ],
                    ),
                    html.Div(className="sub", children="Portfolio Intelligence · AI-Powered"),
                    html.Div(
                        id="login-form",
                        children=[
                            dcc.Input(id="login-email", type="email", placeholder="邮箱", autoComplete="email"),
                            dcc.Input(id="login-password", type="password", placeholder="密码", autoComplete="current-password"),
                            html.Button("进入本地模式", id="login-local", n_clicks=0),
                            html.Button("登录", id="login-submit", n_clicks=0),
                        ],
                    ),
                    html.Div(id="login-error", style={"color": "#E53935", "fontSize": 12, "marginTop": 8}),
                ],
            ),
        ],
    )
