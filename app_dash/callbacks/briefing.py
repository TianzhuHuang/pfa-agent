"""Briefing page callbacks"""

import json
import dash
from dash import Input, Output
from html import escape

import dash.html as html
from pfa.theme_utils import COLORS


def register_briefing_callbacks(app: dash.Dash):
    @app.callback(
        Output("briefing-holdings-check", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def _check_holdings(pathname):
        if pathname != "/briefing":
            return ""
        try:
            from agents.secretary_agent import load_portfolio
            p = load_portfolio()
            holdings = p.get("holdings", [])
            if not holdings:
                return html.Div("请先添加持仓。", style={"color": "#FB8C00", "marginBottom": "16px"})
        except Exception:
            pass
        return ""

    @app.callback(
        Output("briefing-status", "children"),
        Output("briefing-result", "children"),
        Input("briefing-generate", "n_clicks"),
        prevent_initial_call=True,
    )
    def _generate_briefing(n_clicks):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        try:
            from agents.secretary_agent import load_portfolio, run_full_pipeline
            p = load_portfolio()
            holdings = p.get("holdings", [])
            if not holdings:
                return "请先添加持仓。", []
            result = run_full_pipeline(holdings, hours=24, do_audit=False)
            if result.get("status") != "ok":
                return result.get("error", "生成失败"), []
            ar = result.get("analyst_result", {})
            briefing = ar.get("briefing")
            if not briefing:
                try:
                    raw = (ar.get("analysis") or "{}").replace("\uFFFD", "")
                    raw = "".join(c for c in raw if c in "\n\t\r" or (ord(c) >= 32 and ord(c) != 127))
                    briefing = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    briefing = None
            if not briefing:
                return "完成（无结构化结果）", [html.Pre(ar.get("analysis", ""), style={"background": "#1a2c38", "padding": "16px", "borderRadius": "8px", "overflow": "auto", "fontSize": "13px", "color": "#E8EAED"})]
            # Render structured briefing
            ms = briefing.get("market_sentiment", {})
            score = ms.get("score", 50)
            label = ms.get("label", "Neutral")
            s_color = COLORS["up"] if label == "Bullish" else COLORS["down"] if label == "Bearish" else "#5F6368"
            children = [
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "padding": "16px", "background": "#1a2c38", "borderRadius": "8px", "marginBottom": "16px", "boxShadow": "0 4px 12px rgba(0,0,0,0.2)"},
                    children=[
                        html.Div([
                            html.Div(style={"fontSize": "14px", "color": s_color, "fontWeight": 600}, children=f"● {label}"),
                            html.Div(style={"fontSize": "13px", "color": "#9AA0A6"}, children=escape(ms.get("reason", ""))),
                        ]),
                        html.Div(style={"fontSize": "24px", "fontWeight": 700, "color": s_color}, children=str(score)),
                    ],
                ),
            ]
            for item in briefing.get("must_reads", [])[:5]:
                children.append(
                    html.Div(
                        style={"padding": "16px", "background": "#1a2c38", "borderRadius": "8px", "marginBottom": "12px", "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"},
                        children=[
                            html.Div(style={"fontSize": "14px", "fontWeight": 600, "color": "#E8EAED", "marginBottom": "8px"}, children=escape(str(item.get("title", "")))),
                            html.Div(style={"fontSize": "13px", "color": "#9AA0A6", "lineHeight": 1.5}, children=escape(str(item.get("summary", "")))),
                            html.Div(style={"fontSize": "12px", "color": "#5F6368", "marginTop": "8px"}, children=f"💼 {escape(str(item.get('impact_on_portfolio', '')))}"),
                        ],
                    )
                )
            one = briefing.get("one_liner", "")
            if one:
                children.append(html.Blockquote(one, style={"borderLeft": "4px solid #00e701", "paddingLeft": "16px", "color": "#9AA0A6", "marginTop": "16px"}))
            return "生成完成", children
        except Exception as e:
            return f"错误: {e}", []
