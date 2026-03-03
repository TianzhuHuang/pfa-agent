"""Entry modal — 录入持仓：智能搜索 / 截图识别 / 文件导入，支持选择账户"""

import dash.html as html
import dash.dcc as dcc


def entry_modal(account_options: list = None) -> html.Div:
    """Modal: 3 tabs (搜索/截图/文件) + 账户选择."""
    accounts = account_options or ["默认"]
    if "默认" not in accounts:
        accounts = ["默认"] + list(accounts)
    if "新建账户" not in accounts:
        accounts = list(accounts) + ["新建账户"]

    return html.Div(
        id="entry-modal-backdrop",
        className="stake-modal-backdrop",
        style={
            "display": "none",
            "position": "fixed",
            "top": 0,
            "left": 0,
            "right": 0,
            "bottom": 0,
            "background": "rgba(0,0,0,0.7)",
            "zIndex": 1000,
            "alignItems": "center",
            "justifyContent": "center",
        },
        children=[
            html.Div(
                id="entry-modal-content",
                className="stake-modal-content",
                style={
                    "background": "#1a2c38",
                    "borderRadius": "12px",
                    "boxShadow": "0 16px 48px rgba(0,0,0,0.4)",
                    "padding": "24px",
                    "maxWidth": "560px",
                    "width": "95%",
                },
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
                        children=[
                            html.H3("录入持仓", style={"margin": 0, "color": "#E8EAED", "fontSize": "18px", "fontWeight": 600}),
                            html.Button(
                                "×",
                                id="close-entry-modal",
                                n_clicks=0,
                                style={
                                    "background": "none",
                                    "border": "none",
                                    "color": "#9AA0A6",
                                    "fontSize": "24px",
                                    "cursor": "pointer",
                                    "padding": "0 4px",
                                    "lineHeight": 1,
                                },
                            ),
                        ],
                    ),
                    # 账户选择（选择已有账户或新建账户）
                    html.Div(
                        style={"marginBottom": "16px"},
                        children=[
                            html.Div(style={"fontSize": "13px", "fontWeight": 500, "color": "#E8EAED", "marginBottom": "8px"}, children="导入到账户"),
                            html.Div(
                                style={"display": "flex", "gap": "12px", "alignItems": "center"},
                                children=[
                                    dcc.Dropdown(
                                        id="entry-account",
                                        options=[{"label": a, "value": a} for a in accounts],
                                        value=accounts[0] if accounts else "默认",
                                        clearable=False,
                                        style={"flex": 1, "minWidth": "180px"},
                                    ),
                                    html.Div(
                                        id="entry-new-account-wrap",
                                        style={"flex": 1, "display": "none"},
                                        children=[
                                            dcc.Input(
                                                id="entry-new-account-name",
                                                placeholder="输入新账户名称（选择「新建账户」后显示）",
                                                type="text",
                                                className="stake-input",
                                                style={"width": "100%", "padding": "10px 14px", "background": "#243946", "border": "1px solid transparent", "borderRadius": "8px", "color": "#E8EAED", "fontSize": "14px", "boxSizing": "border-box"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Hr(style={"border": "none", "borderTop": "1px solid rgba(255,255,255,0.08)", "margin": "16px 0"}),
                    # Tabs — 智能搜索 / 截图识别 / 文件导入（Stake 深色主题）
                    dcc.Tabs(
                        id="entry-tabs",
                        value="search",
                        parent_className="entry-tabs-parent",
                        className="entry-tabs-stake",
                        colors={
                            "border": "rgba(255,255,255,0.08)",
                            "primary": "#00e701",
                            "background": "#1a2c38",
                        },
                        children=[
                            dcc.Tab(
                                label="智能搜索",
                                value="search",
                                className="entry-tab",
                                selected_className="entry-tab--selected",
                                children=[
                                    html.Div(
                                        style={"padding": "16px 0"},
                                        children=[
                                            html.Div(style={"fontSize": "13px", "color": "#b1bad3", "marginBottom": "8px"}, children="搜索股票代码或名称"),
                                            dcc.Input(
                                                id="entry-search-input",
                                                placeholder="输入股票名或代码",
                                                type="text",
                                                debounce=True,
                                                className="stake-input",
                                                style={
                                                    "width": "100%",
                                                    "padding": "12px 16px",
                                                    "marginBottom": "12px",
                                                    "background": "#243946",
                                                    "border": "1px solid transparent",
                                                    "borderRadius": "8px",
                                                    "color": "#E8EAED",
                                                    "fontSize": "14px",
                                                    "boxSizing": "border-box",
                                                },
                                            ),
                                            html.Div(id="entry-search-results", children=[], style={"maxHeight": "180px", "overflowY": "auto"}),
                                        ],
                                    ),
                                ],
                            ),
                            dcc.Tab(
                                label="截图识别",
                                value="ocr",
                                className="entry-tab",
                                selected_className="entry-tab--selected",
                                children=[
                                    html.Div(
                                        style={"padding": "16px 0"},
                                        children=[
                                            html.Div(style={"fontSize": "13px", "color": "#b1bad3", "marginBottom": "8px"}, children="上传券商持仓截图，AI 识别后确认导入"),
                                            dcc.Upload(
                                                id="entry-ocr-upload",
                                                children=html.Div(
                                                    ["拖拽上传或 ", html.A("点击选择", href="#", style={"color": "#00e701"})],
                                                    style={
                                                        "padding": "24px",
                                                        "border": "1px dashed rgba(255,255,255,0.2)",
                                                        "borderRadius": "8px",
                                                        "textAlign": "center",
                                                        "color": "#b1bad3",
                                                        "fontSize": "14px",
                                                        "cursor": "pointer",
                                                    },
                                                ),
                                                accept="image/*",
                                            ),
                                            html.Div(id="entry-ocr-status", style={"fontSize": "13px", "color": "#b1bad3", "marginTop": "8px"}),
                                            html.Div(id="entry-ocr-preview", children=[], style={"marginTop": "12px", "maxHeight": "200px", "overflowY": "auto"}),
                                            html.Button(
                                                "确认导入",
                                                id="entry-ocr-confirm",
                                                n_clicks=0,
                                                style={"marginTop": "12px", "padding": "10px 20px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "fontWeight": 500},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dcc.Tab(
                                label="文件导入",
                                value="file",
                                className="entry-tab",
                                selected_className="entry-tab--selected",
                                children=[
                                    html.Div(
                                        style={"padding": "16px 0"},
                                        children=[
                                            html.Div(style={"fontSize": "13px", "color": "#b1bad3", "marginBottom": "8px"}, children="上传 CSV 或 JSON 文件（表头含 symbol,name,market）"),
                                            dcc.Upload(
                                                id="entry-file-upload",
                                                children=html.Div(
                                                    ["拖拽上传或 ", html.A("点击选择", href="#", style={"color": "#00e701"})],
                                                    style={
                                                        "padding": "24px",
                                                        "border": "1px dashed rgba(255,255,255,0.2)",
                                                        "borderRadius": "8px",
                                                        "textAlign": "center",
                                                        "color": "#b1bad3",
                                                        "fontSize": "14px",
                                                        "cursor": "pointer",
                                                    },
                                                ),
                                                accept=".csv,.json",
                                            ),
                                            html.Div(id="entry-file-status", style={"fontSize": "13px", "color": "#b1bad3", "marginTop": "8px"}),
                                            html.Div(id="entry-file-preview", children=[], style={"marginTop": "12px", "maxHeight": "200px", "overflowY": "auto"}),
                                            html.Button(
                                                "确认导入",
                                                id="entry-file-confirm",
                                                n_clicks=0,
                                                style={"marginTop": "12px", "padding": "10px 20px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "8px", "cursor": "pointer", "fontSize": "14px", "fontWeight": 500},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dcc.Store(id="entry-ocr-data", data=None),
                    dcc.Store(id="entry-file-data", data=None),
                ],
            ),
        ],
    )
