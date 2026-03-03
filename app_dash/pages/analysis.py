"""Analysis page — 分析中心，Stake 风格"""

import json
import dash.html as html
import dash.dcc as dcc
from html import escape

from pfa.theme_utils import COLORS
from app_dash.components.chat import chat_component


def analysis_page(holdings: list, val: dict, chat_initial: list, user_id: str) -> html.Div:
    """Analysis center: pipeline control + chat."""
    sym_options = [{"label": f"{h.get('name','')}({h.get('symbol','')})", "value": h.get("symbol", "")} for h in holdings] if holdings else []

    return html.Div(
        className="main-content",
        style={"display": "flex", "flex": 1, "height": "calc(100vh - 48px)", "padding": "0", "background": "#0f212e"},
        children=[
            html.Div(
                style={"flex": "0 0 60%", "padding": "24px", "overflowY": "auto"},
                children=[
                    html.H1("分析中心", style={"fontSize": "20px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "24px"}),
                    html.Div(
                        id="analysis-holdings-check",
                        style={"marginBottom": "16px"},
                    ),
                    html.Div(
                        style={
                            "padding": "16px",
                            "background": "#1a2c38",
                            "borderRadius": "8px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.2)",
                            "marginBottom": "24px",
                        },
                        children=[
                            html.Div(style={"fontSize": "12px", "fontWeight": 600, "color": "#9AA0A6", "marginBottom": "12px"}, children="分析控制台"),
                            html.Div(
                                style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
                                children=[
                                    dcc.Dropdown(
                                        id="analysis-symbol",
                                        options=sym_options,
                                        value=sym_options[0]["value"] if sym_options else None,
                                        placeholder="选择标的",
                                        style={"minWidth": "180px", "flex": 1},
                                    ),
                                    html.Button(
                                        "Scout: 抓取该标的",
                                        id="analysis-scout",
                                        n_clicks=0,
                                        className="stake-btn-secondary",
                                        style={"padding": "10px 20px", "background": "#243946", "color": "#E8EAED", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px"},
                                    ),
                                    html.Button(
                                        "运行完整流水线",
                                        id="analysis-pipeline",
                                        n_clicks=0,
                                        className="stake-btn",
                                        style={"padding": "10px 20px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "fontWeight": 500},
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(id="analysis-status", style={"fontSize": "14px", "color": "#9AA0A6", "marginBottom": "16px"}),
                    html.Div(id="analysis-result", children=[]),
                ],
            ),
            html.Div(
                style={"flex": "1", "display": "flex", "flexDirection": "column", "minWidth": 0},
                children=[
                    chat_component(initial_messages=chat_initial, user_id=user_id),
                ],
            ),
        ],
    )
