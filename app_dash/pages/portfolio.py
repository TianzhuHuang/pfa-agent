"""Portfolio page — Stake 风格持仓大盘 + Chat"""

import dash.html as html
import dash.dcc as dcc
from pfa.theme_utils import COLORS

from app_dash.components.chat import chat_component
from app_dash.components.holdings_table import holdings_table
from app_dash.components.charts import allocation_pie
from app_dash.components.entry_modal import entry_modal


def _account_options(val: dict) -> list:
    """从持仓和账户定义中收集账户名列表"""
    accounts = set(val.get("by_account", {}).keys())
    try:
        from agents.secretary_agent import load_portfolio
        p = load_portfolio()
        for a in p.get("accounts", []):
            if a.get("name"):
                accounts.add(a["name"])
    except Exception:
        pass
    accounts.discard("")
    if not accounts:
        return ["默认", "新建账户"]
    return ["默认"] + sorted(a for a in accounts if a != "默认") + ["新建账户"]


def portfolio_page(
    holdings: list,
    val: dict,
    chat_initial: list,
    user_id: str,
) -> html.Div:
    """Full portfolio layout: left = metrics + table, right = chat."""
    total_v = val.get("total_value_cny", 0)
    total_pnl = val.get("total_pnl_cny", 0)
    total_pct = val.get("total_pnl_pct", 0)
    pnl_color = COLORS["up"] if total_pnl >= 0 else COLORS["down"]
    sign = "+" if total_pnl >= 0 else ""

    # Flatten holdings for chart
    all_holdings = []
    for acct_data in val.get("by_account", {}).values():
        all_holdings.extend(acct_data.get("holdings", []))

    if not holdings:
        # Empty state
        return html.Div(
            style={"display": "flex", "flex": 1, "height": "calc(100vh - 48px)", "position": "relative"},
            children=[
                html.Div(
                    style={"flex": "0 0 40%", "padding": "24px", "display": "flex", "alignItems": "center", "justifyContent": "center"},
                    children=[
                        html.Div(
                            className="card",
                            style={
                                "textAlign": "center",
                                "padding": "48px 24px",
                                "background": "#1a2c38",
                                "borderRadius": "12px",
                                "boxShadow": "0 8px 24px rgba(0,0,0,0.3)",
                            },
                            children=[
                                html.Div(style={"fontSize": "48px", "marginBottom": "16px"}, children="📊"),
                                html.Div(style={"fontSize": "16px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "12px"}, children="暂无持仓数据"),
                                html.Div(style={"fontSize": "14px", "color": "#9AA0A6", "lineHeight": 1.6}, children="点击「录入持仓」或通过右侧 AI 对话添加持仓"),
                                html.Button(
                                    "录入持仓",
                                    id="open-entry-modal",
                                    n_clicks=0,
                                    className="stake-btn",
                                    style={"marginTop": "16px", "padding": "10px 24px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "fontWeight": 500},
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "display": "flex", "flexDirection": "column", "minWidth": 0},
                    children=[
                        chat_component(initial_messages=chat_initial, user_id=user_id),
                    ],
                ),
                entry_modal(account_options=_account_options(val)),
            ],
        )

    # Has holdings: two columns
    pie_fig = allocation_pie(all_holdings, total_v) if all_holdings else None

    left_col = html.Div(
        style={"flex": "0 0 55%", "padding": "24px", "overflowY": "auto"},
        children=[
            html.Div(
                style={"display": "flex", "gap": "16px", "marginBottom": "24px", "flexWrap": "wrap"},
                children=[
                    html.Div(
                        className="card",
                        style={
                            "flex": 1,
                            "minWidth": "180px",
                            "padding": "16px",
                            "background": "#1a2c38",
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.2)",
                        },
                        children=[
                            html.Div(style={"fontSize": "12px", "color": "#9AA0A6", "marginBottom": "4px"}, children="Total Wealth"),
                            html.Div(style={"fontSize": "24px", "fontWeight": 700, "color": "#E8EAED"}, children=f"¥{total_v:,.0f}"),
                            html.Div(style={"fontSize": "14px", "color": pnl_color}, children=f"{sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)"),
                        ],
                    ),
                    html.Div(
                        className="card",
                        style={
                            "flex": 1,
                            "minWidth": "120px",
                            "padding": "16px",
                            "background": "#1a2c38",
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.2)",
                        },
                        children=[
                            html.Div(style={"fontSize": "12px", "color": "#9AA0A6", "marginBottom": "4px"}, children="标的 / 账户"),
                            html.Div(style={"fontSize": "20px", "fontWeight": 600, "color": "#E8EAED"}, children=f"{val.get('holding_count', 0)} / {val.get('account_count', 0)}"),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"marginBottom": "24px"},
                children=[
                    dcc.Graph(figure=pie_fig, config={"displayModeBar": False}, style={"height": 280}) if pie_fig else None,
                ],
            ),
            html.Div(style={"fontSize": "14px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "12px"}, children="持仓明细"),
            holdings_table(val.get("by_account", {}), ccy_symbol="¥", ccy_factor=1.0),
            html.Button(
                "录入持仓",
                id="open-entry-modal",
                n_clicks=0,
                className="stake-btn",
                style={"marginTop": "16px", "padding": "10px 20px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "fontWeight": 500},
            ),
        ],
    )

    right_col = html.Div(
        style={"flex": "1", "display": "flex", "flexDirection": "column", "minWidth": 0},
        children=[
            chat_component(initial_messages=chat_initial, user_id=user_id),
        ],
    )

    return html.Div(
        style={"display": "flex", "flex": 1, "height": "calc(100vh - 48px)", "position": "relative"},
        children=[
            html.Div(style={"display": "flex", "flex": 1}, children=[left_col, right_col]),
            entry_modal(account_options=_account_options(val)),
        ],
    )
