"""Chat 组件 — 传统 AI Chat 风格，支持流式输出"""

import dash.html as html
import dash.dcc as dcc
from pfa.theme_utils import logo_data_uri


CHIPS = [
    ("分析持仓", "分析一下我的持仓风险"),
    ("扫描风险", "帮我看下今天有哪些异动"),
    ("生成周报", "基于最近新闻，给我一份调仓建议"),
]


def chat_component(initial_messages: list = None, user_id: str = "admin") -> html.Div:
    """Chat 布局：消息区 + 药丸 + 输入框"""
    logo_uri = logo_data_uri()
    return html.Div(
        className="chat-container",
        children=[
            dcc.Store(id="chat-messages-store", data=initial_messages or []),
            dcc.Store(id="chat-stream-store", data=""),
            dcc.Store(id="chat-user-id-store", data=user_id),
            dcc.Interval(id="chat-stream-interval", interval=150, n_intervals=0),
            html.Div(
                className="chat-messages",
                style={"flex": 1, "overflowY": "auto", "padding": "24px", "display": "flex", "flexDirection": "column", "gap": "20px"},
                children=[
                    html.Div(id="chat-messages", children=[]),
                    html.Div(
                        id="chat-current-stream",
                        className="msg assistant chat-bubble",
                        style={"display": "none"},
                        children=[
                            html.Div(className="msg-avatar", children=[html.Img(src=logo_uri, alt="PFA")]),
                            html.Div(className="msg-bubble", id="chat-stream-bubble", children=""),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chat-chips",
                children=[
                    html.Button(label, id={"type": "chat-chip", "index": i}, n_clicks=0)
                    for i, (label, _) in enumerate(CHIPS)
                ],
            ),
            html.Div(
                className="chat-input-row",
                children=[
                    dcc.Input(
                        id="chat-input",
                        placeholder="问问投资的问题...",
                        type="text",
                        debounce=True,
                        autoComplete="off",
                    ),
                    html.Button("发送", id="chat-send", n_clicks=0),
                ],
            ),
        ],
    )


def render_message(role: str, content: str) -> html.Div:
    """Render a single message bubble."""
    logo_uri = logo_data_uri()
    if role == "assistant":
        return html.Div(
            className="msg assistant chat-bubble",
            children=[
                html.Div(className="msg-avatar", children=[html.Img(src=logo_uri, alt="PFA")]),
                html.Div(className="msg-bubble", children=content),
            ],
        )
    return html.Div(
        className="msg user chat-bubble",
        children=[
            html.Div(className="msg-avatar"),
            html.Div(className="msg-bubble", children=content),
        ],
    )
