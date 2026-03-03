"""Analysis page callbacks"""

import json
import dash
from dash import Input, Output
from html import escape

import dash.html as html
from pfa.theme_utils import COLORS


def register_analysis_callbacks(app: dash.Dash):
    @app.callback(
        Output("analysis-holdings-check", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )
    def _check_holdings(pathname):
        if pathname != "/analysis":
            return ""
        try:
            from agents.secretary_agent import load_portfolio
            p = load_portfolio()
            if not p.get("holdings"):
                return html.Div("请先添加持仓。", style={"color": "#FB8C00"})
        except Exception:
            pass
        return ""

    @app.callback(
        Output("analysis-status", "children"),
        Output("analysis-result", "children"),
        Input("analysis-scout", "n_clicks"),
        Input("analysis-pipeline", "n_clicks"),
        Input("analysis-symbol", "value"),
        prevent_initial_call=True,
    )
    def _run_analysis(scout_clicks, pipeline_clicks, symbol):
        if not dash.ctx.triggered_id:
            raise dash.exceptions.PreventUpdate
        triggered = dash.ctx.triggered_id
        try:
            from agents.secretary_agent import load_portfolio, fetch_single_symbol, run_full_pipeline
            p = load_portfolio()
            holdings = p.get("holdings", [])
            if not holdings:
                return "请先添加持仓。", []

            if triggered == "analysis-scout" and symbol:
                h = next((x for x in holdings if x.get("symbol") == symbol), None)
                if h:
                    r = fetch_single_symbol(h["symbol"], h.get("name", ""), h.get("market", "A"), 24)
                    by_src = r.get("by_source", {})
                    detail = " + ".join(f"{s}:{n}" for s, n in by_src.items()) if by_src else ""
                    return f"✅ {r.get('count', 0)} 条 ({detail})", []
                return "未找到标的", []

            if triggered == "analysis-pipeline":
                result = run_full_pipeline(holdings, hours=72, do_audit=True)
                if result.get("status") != "ok":
                    return result.get("error", "失败"), []
                ar = result.get("analyst_result", {})
                briefing = ar.get("briefing") or (json.loads(ar.get("analysis", "{}")) if ar.get("analysis") else None)
                if briefing:
                    ms = briefing.get("market_sentiment", {})
                    s_color = COLORS["up"] if ms.get("label") == "Bullish" else COLORS["down"] if ms.get("label") == "Bearish" else "#5F6368"
                    children = [
                        html.Div(
                            style={"padding": "16px", "background": "#1a2c38", "borderRadius": "8px", "marginBottom": "12px", "boxShadow": "0 4px 12px rgba(0,0,0,0.2)"},
                            children=[
                                html.Div(style={"fontSize": "14px", "color": s_color, "fontWeight": 600}, children=f"● {ms.get('label', '')}"),
                                html.Div(style={"fontSize": "13px", "color": "#9AA0A6"}, children=escape(ms.get("reason", ""))),
                            ],
                        ),
                    ]
                    for item in briefing.get("must_reads", [])[:3]:
                        children.append(html.Div(
                            style={"padding": "12px", "background": "#243946", "borderRadius": "8px", "marginBottom": "8px"},
                            children=[
                                html.Div(style={"fontWeight": 600}, children=escape(str(item.get("title", "")))),
                                html.Div(style={"fontSize": "13px", "color": "#9AA0A6"}, children=escape(str(item.get("summary", "")))),
                            ],
                        ))
                    return "完成", children
                return "完成", [html.Pre(ar.get("analysis", ""), style={"background": "#1a2c38", "padding": "16px", "borderRadius": "8px", "overflow": "auto", "fontSize": "12px", "color": "#E8EAED"})]
        except Exception as e:
            return f"错误: {e}", []
        raise dash.exceptions.PreventUpdate
