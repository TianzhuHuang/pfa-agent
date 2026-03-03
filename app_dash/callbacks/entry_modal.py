"""Entry modal callbacks — 打开/关闭、搜索、OCR、文件导入、账户选择"""

import base64
import csv
import io
import json
import dash
from dash import Input, Output, State, ctx
from datetime import datetime

import dash.html as html

from pfa.stock_search import search_stock
from pfa.screenshot_ocr import extract_holdings_from_image
from agents.secretary_agent import (
    load_portfolio,
    save_portfolio,
    parse_csv_holdings,
    parse_json_holdings,
    update_holdings_bulk,
    upsert_account,
)


def _resolve_account(account_val, new_name_val):
    """解析最终账户名：新建账户时用输入框值"""
    if account_val == "新建账户" and (new_name_val or "").strip():
        return (new_name_val or "").strip()
    return (account_val or "默认").strip() or "默认"


def register_entry_modal_callbacks(app: dash.Dash):
    @app.callback(
        Output("entry-modal-backdrop", "style"),
        Input("open-entry-modal", "n_clicks"),
        Input("close-entry-modal", "n_clicks"),
        prevent_initial_call=True,
    )
    def _toggle_modal(open_clicks, close_clicks):
        triggered = ctx.triggered_id
        if triggered == "open-entry-modal" and open_clicks:
            return {"display": "flex", "position": "fixed", "top": 0, "left": 0, "right": 0, "bottom": 0, "background": "rgba(0,0,0,0.6)", "zIndex": 1000, "alignItems": "center", "justifyContent": "center"}
        return {"display": "none", "position": "fixed", "top": 0, "left": 0, "right": 0, "bottom": 0, "background": "rgba(0,0,0,0.6)", "zIndex": 1000, "alignItems": "center", "justifyContent": "center"}

    @app.callback(
        Output("entry-new-account-wrap", "style"),
        Input("entry-account", "value"),
    )
    def _show_new_account(account_val):
        if account_val == "新建账户":
            return {"flex": 1, "display": "block"}
        return {"flex": 1, "display": "none"}

    @app.callback(
        Output("entry-search-results", "children"),
        Input("entry-search-input", "value"),
        prevent_initial_call=True,
    )
    def _search_stocks(value):
        if not value or len(value.strip()) < 1:
            return []
        results = search_stock(value.strip(), count=8)
        if not results:
            return [html.Div("未找到结果", style={"padding": "12px", "color": "#b1bad3", "fontSize": "14px"})]
        children = []
        for i, r in enumerate(results):
            children.append(
                html.Div(
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "padding": "12px 14px",
                        "background": "rgba(36, 57, 70, 0.5)" if i % 2 == 1 else "transparent",
                        "borderRadius": "4px",
                    },
                    children=[
                        html.Div(
                            style={"fontSize": "14px", "color": "#E8EAED"},
                            children=f"{r.get('code', '')} {r.get('name', '')}",
                        ),
                        html.Button(
                            "添加",
                            id={"type": "entry-add", "index": i, "code": r.get("code", ""), "name": r.get("name", ""), "market": r.get("market", "A")},
                            n_clicks=0,
                            style={"padding": "6px 14px", "background": "#00e701", "color": "#0f212e", "border": "none", "borderRadius": "6px", "cursor": "pointer", "fontSize": "13px", "fontWeight": 500},
                        ),
                    ],
                )
            )
        return children

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input({"type": "entry-add", "index": dash.ALL}, "n_clicks"),
        State("entry-account", "value"),
        State("entry-new-account-name", "value"),
        prevent_initial_call=True,
    )
    def _add_holding(n_clicks_list, account_val, new_name_val):
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "entry-add":
            raise dash.exceptions.PreventUpdate
        code = triggered.get("code", "")
        name = triggered.get("name", "")
        market = triggered.get("market", "A")
        if code:
            account = _resolve_account(account_val, new_name_val)
            if account and account != "默认":
                upsert_account(account)
            p = load_portfolio()
            entry = {
                "symbol": code,
                "name": name,
                "market": market,
                "quantity": 0,
                "cost_price": 0,
                "source": "search",
                "account": account,
                "updated_at": datetime.now().isoformat(),
            }
            p.setdefault("holdings", []).append(entry)
            save_portfolio(p)
            return "/"
        raise dash.exceptions.PreventUpdate

    # OCR upload
    @app.callback(
        Output("entry-ocr-data", "data"),
        Output("entry-ocr-status", "children"),
        Output("entry-ocr-preview", "children"),
        Input("entry-ocr-upload", "contents"),
        prevent_initial_call=True,
    )
    def _ocr_upload(contents):
        if not contents:
            raise dash.exceptions.PreventUpdate
        try:
            content_type, b64 = contents.split(",")
            mime = "image/png"
            if "jpeg" in content_type or "jpg" in content_type:
                mime = "image/jpeg"
            elif "webp" in content_type:
                mime = "image/webp"
            img_bytes = base64.b64decode(b64)
            r = extract_holdings_from_image(img_bytes, mime)
            if r["status"] == "ok" and r.get("holdings"):
                holdings = r["holdings"]
                preview = []
                for i, h in enumerate(holdings[:10]):
                    preview.append(
                        html.Div(
                            style={"padding": "8px 12px", "fontSize": "13px", "color": "#E8EAED", "background": "rgba(36,57,70,0.5)" if i % 2 == 1 else "transparent", "borderRadius": "4px"},
                            children=f"{h.get('symbol','')} {h.get('name','')} × {h.get('quantity',0)} @ {h.get('cost_price',0)}",
                        )
                    )
                if len(holdings) > 10:
                    preview.append(html.Div(style={"fontSize": "12px", "color": "#b1bad3"}, children=f"... 共 {len(holdings)} 条"))
                return holdings, f"识别到 {len(holdings)} 条，请确认后导入", preview
            return None, r.get("error", "识别失败"), []
        except Exception as e:
            return None, str(e), []

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("entry-ocr-data", "data", allow_duplicate=True),
        Input("entry-ocr-confirm", "n_clicks"),
        State("entry-ocr-data", "data"),
        State("entry-account", "value"),
        State("entry-new-account-name", "value"),
        prevent_initial_call=True,
    )
    def _ocr_confirm(n_clicks, ocr_data, account_val, new_name_val):
        if not n_clicks or not ocr_data:
            raise dash.exceptions.PreventUpdate
        account = _resolve_account(account_val, new_name_val)
        if account and account != "默认":
            upsert_account(account)
        p = load_portfolio()
        now = datetime.now().isoformat()
        for h in ocr_data:
            sym = str(h.get("symbol", "")).strip()
            if not sym:
                continue
            e = {
                "symbol": sym,
                "name": str(h.get("name", "")),
                "market": str(h.get("market", "A"))[:2] or "A",
                "source": "ocr",
                "account": account,
                "updated_at": now,
            }
            for k in ("cost_price", "quantity"):
                v = h.get(k)
                if v is not None and (isinstance(v, (int, float)) or v):
                    try:
                        e[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            p.setdefault("holdings", []).append(e)
        save_portfolio(p)
        return "/", None

    # File upload
    @app.callback(
        Output("entry-file-data", "data"),
        Output("entry-file-status", "children"),
        Output("entry-file-preview", "children"),
        Input("entry-file-upload", "contents"),
        State("entry-file-upload", "filename"),
        prevent_initial_call=True,
    )
    def _file_upload(contents, filename):
        if not contents or not filename:
            raise dash.exceptions.PreventUpdate
        try:
            content_type, b64 = contents.split(",")
            raw = base64.b64decode(b64).decode("utf-8")
            if filename.lower().endswith(".csv"):
                holdings = parse_csv_holdings(raw)
            else:
                holdings = parse_json_holdings(raw)
            if not holdings:
                return None, "未解析到有效数据", []
            preview = []
            for i, h in enumerate(holdings[:10]):
                preview.append(
                    html.Div(
                        style={"padding": "8px 12px", "fontSize": "13px", "color": "#E8EAED", "background": "rgba(36,57,70,0.5)" if i % 2 == 1 else "transparent", "borderRadius": "4px"},
                        children=f"{h.get('symbol','')} {h.get('name','')} × {h.get('quantity',0)} @ {h.get('cost_price',0)}",
                    )
                )
            if len(holdings) > 10:
                preview.append(html.Div(style={"fontSize": "12px", "color": "#b1bad3"}, children=f"... 共 {len(holdings)} 条"))
            return holdings, f"解析到 {len(holdings)} 条，请确认后导入", preview
        except Exception as e:
            return None, str(e), []

    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Output("entry-file-data", "data", allow_duplicate=True),
        Input("entry-file-confirm", "n_clicks"),
        State("entry-file-data", "data"),
        State("entry-account", "value"),
        State("entry-new-account-name", "value"),
        prevent_initial_call=True,
    )
    def _file_confirm(n_clicks, file_data, account_val, new_name_val):
        if not n_clicks or not file_data:
            raise dash.exceptions.PreventUpdate
        account = _resolve_account(account_val, new_name_val)
        if account and account != "默认":
            upsert_account(account)
        p = load_portfolio()
        now = datetime.now().isoformat()
        for h in file_data:
            sym = str(h.get("symbol", "")).strip()
            if not sym:
                continue
            e = dict(h)
            e.setdefault("source", "csv")
            e["account"] = account
            e["updated_at"] = now
            p.setdefault("holdings", []).append(e)
        update_holdings_bulk(p["holdings"])
        save_portfolio(p)
        return "/", None
