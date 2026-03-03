"""Briefing page — 综合早报，Stake 风格"""

import json
import dash.html as html
import dash.dcc as dcc
from datetime import datetime, timedelta, timezone
from html import escape

from pfa.theme_utils import COLORS

CST = timezone(timedelta(hours=8))


def briefing_page() -> html.Div:
    now = datetime.now(CST)
    return html.Div(
        className="main-content",
        style={"padding": "24px", "background": "#0f212e"},
        children=[
            html.H1(f"投研晨报 · {now.strftime('%m月%d日')}", style={"fontSize": "20px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "24px"}),
            html.Div(id="briefing-holdings-check"),
            html.Button(
                "生成今日晨报",
                id="briefing-generate",
                n_clicks=0,
                className="stake-btn",
                style={"padding": "12px 24px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "marginBottom": "24px", "fontWeight": 500},
            ),
            html.Div(id="briefing-status", style={"fontSize": "14px", "color": "#9AA0A6", "marginBottom": "16px"}),
            html.Div(id="briefing-result", children=[]),
        ],
    )
