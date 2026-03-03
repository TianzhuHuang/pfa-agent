"""Settings page — 数据源配置，Stake 风格"""

import dash.html as html
import dash.dcc as dcc
from html import escape

from agents.secretary_agent import load_data_sources


def settings_page() -> html.Div:
    sources = load_data_sources()
    rss_list = sources.get("rss_urls", [])
    rss_items = []
    for i, item in enumerate(rss_list):
        url = item.get("url", item) if isinstance(item, dict) else item
        name = item.get("name", "") if isinstance(item, dict) else ""
        rss_items.append(
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "padding": "14px 12px",
                    "background": "rgba(26, 44, 56, 0.3)" if i % 2 == 1 else "transparent",
                    "borderRadius": "4px",
                },
                children=[
                    html.Div([
                        html.Div(style={"fontSize": "14px", "color": "#E8EAED"}, children=escape(name or "—")),
                        html.Div(style={"fontSize": "12px", "color": "#9AA0A6"}, children=escape(url)),
                    ]),
                    html.Button(
                        "删除",
                        id={"type": "settings-del-rss", "index": i, "url": url},
                        n_clicks=0,
                        style={"padding": "6px 12px", "background": "transparent", "color": "#E53935", "border": "none", "borderRadius": "6px", "cursor": "pointer", "fontSize": "12px"},
                    ),
                ],
            )
        )
    return html.Div(
        className="main-content",
        style={"padding": "24px", "background": "#0f212e"},
        children=[
            html.H1("数据源配置", style={"fontSize": "20px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "24px"}),
            html.Div(
                style={"fontSize": "13px", "color": "#9AA0A6", "marginBottom": "16px"},
                children=f"RSS: {len(rss_list)} 条 · 保存后立即生效",
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
                    html.Div(style={"fontSize": "12px", "fontWeight": 600, "color": "#9AA0A6", "marginBottom": "12px"}, children="RSS 订阅"),
                    html.Div(id="settings-rss-list", children=rss_items),
                    html.Div(
                        style={"display": "flex", "gap": "12px", "marginTop": "16px"},
                        children=[
                            dcc.Input(
                                id="settings-rss-url",
                                placeholder="RSS URL",
                                style={"flex": 1, "padding": "10px", "background": "#243946", "border": "1px solid transparent", "borderRadius": "8px", "color": "#E8EAED"},
                            ),
                            dcc.Input(
                                id="settings-rss-name",
                                placeholder="名称",
                                style={"flex": 1, "padding": "10px", "background": "#243946", "border": "1px solid transparent", "borderRadius": "8px", "color": "#E8EAED"},
                            ),
                            html.Button(
                                "添加 RSS",
                                id="settings-add-rss",
                                n_clicks=0,
                                className="stake-btn",
                                style={"padding": "10px 20px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontWeight": 500},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
