# -*- coding: utf-8 -*-
"""
Portfolio API — 持仓数据与估值

复用 pfa/portfolio_valuation.py 与 agents/secretary_agent.py。
"""

import sys
from pathlib import Path

# 将项目根目录加入 path，以便 import pfa 和 agents
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()

# 避免 traceback 格式化时的 UTF-8 解码问题
_DEFAULT_ACCOUNT = "\u9ed8\u8ba4"  # 默认


class AddHoldingRequest(BaseModel):
    symbol: str
    name: str
    market: str = "A"
    account: str = "默认"
    new_account_name: str = ""
    new_account_currency: str = "CNY"
    quantity: float = 0
    cost_price: float = 0


class AddHoldingsBulkRequest(BaseModel):
    holdings: List[Dict[str, Any]]
    account: str = "默认"
    new_account_name: str = ""
    new_account_currency: str = "CNY"
    available_balance: Optional[float] = None


class TradeConfirmRequest(BaseModel):
    """确认写入：对话驱动交易的最终确认。"""
    action: str  # add | update | remove
    symbol: str
    name: str = ""
    market: str = "A"
    quantity: float = 0
    cost_price: float = 0
    account: str = "默认"


def _load_portfolio() -> Dict:
    from agents.secretary_agent import load_portfolio
    return load_portfolio()


def _get_valuation(display_currency: str = "CNY") -> Dict:
    from agents.secretary_agent import load_portfolio
    from pfa.portfolio_valuation import calculate_portfolio_value, get_realtime_prices, get_fx_rates, get_fx_updated_at
    p = load_portfolio()
    holdings = p.get("holdings", [])
    accounts = p.get("accounts", [])
    if not holdings:
        fx_raw = get_fx_rates()
        val = {
            "total_value_cny": 0,
            "total_cost_cny": 0,
            "total_pnl_cny": 0,
            "total_pnl_pct": 0,
            "holding_count": 0,
            "account_count": 0,
            "by_account": {},
            "target_currency": display_currency if display_currency != "original" else "CNY",
            "fx_updated_at": get_fx_updated_at(),
            "fx_rates": {k: round(v, 4) for k, v in fx_raw.items()},
        }
    else:
        prices = get_realtime_prices(holdings)
        val = calculate_portfolio_value(holdings, prices, target_currency=display_currency)

    # Merge account balances into valuation
    fx = val.get("fx_rates") or get_fx_rates()
    target_cur = val.get("target_currency", "CNY")
    is_original = (target_cur or "").strip().lower() == "original"

    for acc in accounts:
        acct_name = str(acc.get("name", acc.get("id", ""))).strip()
        if not acct_name:
            continue
        balance = float(acc.get("balance", 0) or 0)
        if balance <= 0:
            continue
        base_cur = str(acc.get("base_currency", acc.get("currency", "CNY"))).strip().upper() or "CNY"
        rate_from = fx.get(base_cur) or 1.0
        rate_to = 1.0 if (is_original or target_cur == "CNY") else (fx.get(target_cur) or 1.0)
        if rate_to <= 0:
            rate_to = 1.0
        balance_cny = balance * rate_from
        balance_target = balance_cny / rate_to if not is_original and target_cur != "CNY" else balance_cny

        if acct_name not in val["by_account"]:
            val["by_account"][acct_name] = {"value": 0, "cost": 0, "pnl": 0, "holdings": []}
        val["by_account"][acct_name]["value"] = val["by_account"][acct_name]["value"] + balance_target
        val["total_value_cny"] = round((val.get("total_value_cny") or 0) + balance_target, 2)

        cash_row = {
            "symbol": "CASH",
            "name": "💰 现金余额",
            "is_cash": True,
            "current_price": 1.0,
            "cost_price": 1.0,
            "quantity": balance,
            "value_local": balance,
            "value_cny": round(balance_target, 2),
            "value_display": round(balance_target, 2),
            "currency": base_cur,
            "account": acct_name,
            "pnl_cny": 0,
            "pnl_pct": 0,
            "today_pct": 0,
            "position_pct": 0,
        }
        val["by_account"][acct_name]["holdings"].append(cash_row)

    # Recalculate position_pct for all holdings (including cash)
    for acct_data in val["by_account"].values():
        acct_val = acct_data["value"]
        for ho in acct_data["holdings"]:
            v = ho.get("value_cny", ho.get("value_local", 0))
            ho["position_pct"] = round((v / acct_val * 100), 1) if acct_val > 0 else 0

    val["account_count"] = len(val["by_account"])
    return val


@router.get("/portfolio")
def get_portfolio(display_currency: str = "CNY"):
    """获取持仓估值与明细。display_currency: CNY | USD | original"""
    val = _get_valuation(display_currency)
    return val


@router.get("/portfolio/fx")
def get_fx():
    """返回当前汇率与更新时间。"""
    from pfa.portfolio_valuation import get_fx_rates, get_fx_updated_at
    rates = get_fx_rates()
    return {"rates": rates, "updated_at": get_fx_updated_at()}


@router.get("/portfolio/raw")
def get_portfolio_raw():
    """获取原始 portfolio JSON（含 channels、accounts 等）。"""
    return _load_portfolio()


@router.get("/portfolio/feed")
def get_feed(symbol: str = "", since_hours: int = 72):
    """获取该标的的 FeedItem 列表（新闻/RSS/雪球等）。"""
    sym = (symbol or "").strip()
    if not sym:
        return {"items": []}
    try:
        from pfa.data.store import load_all_feed_items
        items = load_all_feed_items(symbol=sym, since_hours=since_hours)
        return {"items": [it.to_dict() for it in items]}
    except Exception as e:
        return {"items": [], "error": str(e)[:80]}


@router.post("/portfolio/fetch-news")
def fetch_news(symbol: str = "", hours: int = 72):
    """触发 Scout 抓取该股新闻。"""
    sym = (symbol or "").strip()
    if not sym:
        return {"ok": False, "error": "symbol 必填"}
    p = _load_portfolio()
    holdings = p.get("holdings", [])
    holding = next((h for h in holdings if str(h.get("symbol", "")).strip() == sym), None)
    if not holding:
        return {"ok": False, "error": "未持有该标的"}
    name = str(holding.get("name", sym)).strip() or sym
    market = str(holding.get("market", "A")).strip() or "A"
    try:
        from agents.secretary_agent import fetch_single_symbol
        r = fetch_single_symbol(sym, name, market, hours)
        if r.get("status") == "ok":
            count = r.get("count", 0)
            return {"ok": True, "count": count}
        return {"ok": False, "error": r.get("error", "抓取失败")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


@router.post("/portfolio/sentiment")
def analyze_sentiment(symbol: str = ""):
    """对该股新闻做 Analyst 情绪研判。"""
    sym = (symbol or "").strip()
    if not sym:
        return {"ok": False, "label": "暂无情绪"}
    try:
        from pfa.data.store import load_all_feed_items
        import os
        import requests
        import json

        items = load_all_feed_items(symbol=sym, since_hours=72)
        if not items:
            return {"ok": True, "label": "暂无情绪", "reason": "近 72h 无相关新闻"}

        news_lines = []
        for it in items[:15]:
            ts = (it.published_at or "")[:16]
            news_lines.append(f"- [{ts}] {it.title}: {(it.content_snippet or '')[:100]}")
        news_text = "\n".join(news_lines)

        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return {"ok": True, "label": "暂无情绪", "reason": "未配置 DASHSCOPE_API_KEY"}

        prompt = f"""你是一位投研分析师。以下是与标的 {sym} 相关的近期新闻摘要：

{news_text}

请用一句话判断该股当前信息面情绪，严格按以下 JSON 格式输出（不要输出其他文字）：
{{"label": "偏多" 或 "偏空" 或 "中性", "reason": "一句话理由", "score": 0-100 的整数（50=中性）}}"""

        resp = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 200},
            timeout=30,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        content = content.strip().replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(content)
            return {"ok": True, "label": data.get("label", "中性"), "reason": data.get("reason", ""), "score": data.get("score", 50)}
        except json.JSONDecodeError:
            return {"ok": True, "label": "中性", "reason": content[:100] if content else "解析失败", "score": 50}
    except Exception as e:
        return {"ok": False, "label": "暂无情绪", "reason": str(e)[:80]}


@router.get("/portfolio/timeline")
def get_timeline(symbol: str = "", user_id: str = "admin"):
    """返回该标的的时间轴事件（含持仓变动）。"""
    sym = (symbol or "").strip()
    if not sym:
        return {"events": []}
    try:
        from pfa.data.store import get_timeline_events
        events = get_timeline_events(user_id or "admin", sym)
        return {"events": [e.to_dict() for e in events]}
    except Exception as e:
        return {"events": [], "error": str(e)[:80]}


@router.get("/portfolio/search")
def search_stocks(q: str = ""):
    """搜索股票（东方财富 API）。"""
    keyword = (q or "").strip()
    if not keyword:
        return []
    try:
        from pfa.stock_search import search_stock
        results = search_stock(keyword, count=8)
        return results if results else []
    except Exception as e:
        # 东方财富 API 可能超时或网络异常，返回空列表避免前端报错
        import logging
        logging.getLogger("pfa").warning("stock search failed: %s", e)
        return []


@router.get("/portfolio/accounts")
def list_accounts():
    """获取账户列表（含 base_currency, account_type），供 EditAccountsModal 与 EntryModal 使用。"""
    from agents.secretary_agent import get_accounts as _get_accounts
    accs = _get_accounts()
    if not accs:
        p = _load_portfolio()
        existing = sorted({str(h.get("account", "")).strip() for h in p.get("holdings", []) if h.get("account")})
        for name in (existing or ["默认"]):
            if name and name not in [a.get("name") for a in accs]:
                accs.append({"id": name, "name": name, "base_currency": "CNY", "account_type": "股票", "balance": 0})
    if not any(a.get("name") == "默认" for a in accs):
        accs = [{"id": "默认", "name": "默认", "base_currency": "CNY", "account_type": "股票", "balance": 0}] + accs
    return {"accounts": accs}


def _resolve_account(account: str, new_name: str, currency: str = "CNY") -> str:
    if account == "新建账户" and (new_name or "").strip():
        return (new_name or "").strip()
    return (account or "默认").strip() or "默认"


@router.post("/portfolio/holdings")
def add_holding(req: AddHoldingRequest):
    """添加单条持仓（智能搜索后添加）。"""
    from agents.secretary_agent import load_portfolio, save_portfolio, upsert_account
    from datetime import datetime
    acc = _resolve_account(req.account, req.new_account_name)
    currency = (req.new_account_currency or "CNY").strip().upper()
    if acc and acc != _DEFAULT_ACCOUNT:
        upsert_account(acc, broker="", currency=currency, account_type="股票")
    p = load_portfolio()
    qty = max(0, float(req.quantity or 0))
    cost = max(0, float(req.cost_price or 0))
    entry = {
        "symbol": req.symbol.strip(),
        "name": (req.name or "").strip(),
        "market": (req.market or "A")[:2] or "A",
        "quantity": qty,
        "cost_price": cost,
        "source": "search",
        "account": acc,
        "updated_at": datetime.now().isoformat(),
    }
    p.setdefault("holdings", []).append(entry)
    save_portfolio(p)
    return {"ok": True}


class OcrRequest(BaseModel):
    contents: str  # data:image/xxx;base64,...


class ParseFileRequest(BaseModel):
    contents: str  # base64
    filename: str = ""


@router.post("/portfolio/ocr")
def ocr_image(req: OcrRequest):
    """OCR 识别持仓截图，返回识别结果。contents 为 data:image/xxx;base64,... 格式。"""
    contents = req.contents
    if not contents or "base64," not in contents:
        return {"status": "error", "error": "无效的图片数据"}
    try:
        import base64
        import os
        if not os.environ.get("DASHSCOPE_API_KEY"):
            return {"status": "error", "error": "DASHSCOPE_API_KEY 未设置，请在项目根目录 .env 中配置"}
        _, b64 = contents.split(",", 1)
        mime = "image/png"
        if "jpeg" in contents or "jpg" in contents:
            mime = "image/jpeg"
        elif "webp" in contents:
            mime = "image/webp"
        img_bytes = base64.b64decode(b64)
        if len(img_bytes) > 10 * 1024 * 1024:  # 10MB
            return {"status": "error", "error": "图片过大，请压缩后重试"}
        from pfa.screenshot_ocr import extract_holdings_from_image
        r = extract_holdings_from_image(img_bytes, mime)
        if r.get("status") == "ok" and r.get("holdings"):
            out = {"status": "ok", "holdings": r["holdings"]}
            if r.get("available_balance") is not None:
                out["available_balance"] = r["available_balance"]
            return out
        return {"status": "error", "error": r.get("error", "识别失败")}
    except Exception as e:
        err_msg = str(e)
        # 便于本地调试，避免返回过长堆栈
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        return {"status": "error", "error": err_msg}


def _market_to_currency(market: str) -> str:
    """由 market 推断标的原始币种。"""
    return {"A": "CNY", "HK": "HKD", "US": "USD"}.get((market or "A")[:2], "CNY")


@router.post("/portfolio/holdings/bulk")
def add_holdings_bulk(req: AddHoldingsBulkRequest):
    """批量添加持仓（OCR 或文件导入后确认）。"""
    from agents.secretary_agent import load_portfolio, save_portfolio, upsert_account, update_account, update_holdings_bulk
    from pfa.symbol_utils import normalize_hk_symbol
    from datetime import datetime
    acc = _resolve_account(req.account, req.new_account_name)
    currency = (req.new_account_currency or "CNY").strip().upper()
    if acc and acc != _DEFAULT_ACCOUNT:
        upsert_account(acc, broker="", currency=currency, account_type="股票", balance=req.available_balance)
    if acc and req.available_balance is not None and req.available_balance > 0:
        update_account(acc, balance=req.available_balance)
    p = load_portfolio()
    now = datetime.now().isoformat()
    for h in req.holdings:
        sym = str(h.get("symbol", "")).strip()
        if not sym:
            continue
        e = dict(h)
        e["market"] = str(e.get("market", "A"))[:2] or "A"
        if e["market"] == "HK":
            e["symbol"] = normalize_hk_symbol(sym)
        else:
            for suffix in (".HK", ".hk", ".SH", ".sh", ".SZ", ".sz"):
                if sym.upper().endswith(suffix.upper()):
                    sym = sym[: -len(suffix)]
                    break
            e["symbol"] = sym
        e.setdefault("name", "")
        e["account"] = acc
        e["updated_at"] = now
        e.setdefault("source", "ocr")
        if e.get("source") == "ocr":
            e["ocr_confirmed"] = False
        valid_cur = (e.get("currency") or "").strip().upper() in ("CNY", "USD", "HKD")
        e["currency"] = (e.get("currency") or "").strip().upper() if valid_cur else _market_to_currency(e["market"])
        if e.get("exchange"):
            e["exchange"] = str(e.get("exchange", "")).strip()
        for k in ("cost_price", "quantity"):
            v = e.get(k)
            if v is not None:
                try:
                    e[k] = float(v)
                except (ValueError, TypeError):
                    pass
        p.setdefault("holdings", []).append(e)
    update_holdings_bulk(p["holdings"])
    save_portfolio(p)
    return {"ok": True}


@router.post("/portfolio/trade/confirm")
def trade_confirm(req: TradeConfirmRequest):
    """确认写入：用户点击「确认写入」后调用，真正更新持仓。"""
    from agents.secretary_agent import load_portfolio, save_portfolio, update_holding, upsert_account
    from fastapi import HTTPException
    from datetime import datetime

    sym = (req.symbol or "").strip()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol 必填")
    acc = (req.account or "默认").strip() or "默认"
    if acc and acc != _DEFAULT_ACCOUNT:
        upsert_account(acc, broker="", currency="CNY", account_type="股票")

    p = load_portfolio()
    holdings = p.get("holdings", [])

    if req.action == "add":
        now = datetime.now().isoformat()
        new_qty = float(req.quantity or 0)
        new_cost = float(req.cost_price or 0)
        # 若已有同标的同账户，则累加数量并更新成本价（加权平均），不新增一条
        for h in p.get("holdings", []):
            if str(h.get("symbol", "")).strip() == sym and str(h.get("account", "")).strip() == acc:
                old_qty = float(h.get("quantity", 0) or 0)
                old_cost = float(h.get("cost_price", 0) or 0)
                total_qty = old_qty + new_qty
                if total_qty > 0 and (old_cost > 0 or new_cost > 0):
                    # 加权平均成本
                    h["cost_price"] = round((old_qty * old_cost + new_qty * new_cost) / total_qty, 4)
                elif new_cost > 0:
                    h["cost_price"] = new_cost
                h["quantity"] = total_qty
                if req.name and (req.name or "").strip():
                    h["name"] = (req.name or "").strip()
                h["updated_at"] = now
                save_portfolio(p)
                return {"ok": True, "action": "update"}
        # 无已有持仓，新增
        entry = {
            "symbol": sym,
            "name": (req.name or "").strip(),
            "market": (req.market or "A")[:2] or "A",
            "quantity": new_qty,
            "cost_price": new_cost,
            "source": "ai_expert",
            "account": acc,
            "updated_at": now,
        }
        p.setdefault("holdings", []).append(entry)
        save_portfolio(p)
        return {"ok": True, "action": "add"}

    if req.action == "update":
        updated = update_holding(sym, acc, quantity=req.quantity, cost_price=req.cost_price, name=req.name or None)
        if updated is None:
            raise HTTPException(status_code=404, detail="未找到该持仓")
        return {"ok": True, "action": "update"}

    if req.action == "remove":
        before = len(holdings)
        p["holdings"] = [
            h for h in holdings
            if not (str(h.get("symbol", "")).strip() == sym and str(h.get("account", "")).strip() == acc)
        ]
        if len(p["holdings"]) < before:
            save_portfolio(p)
            return {"ok": True, "action": "remove"}
        raise HTTPException(status_code=404, detail="未找到该持仓")

    raise HTTPException(status_code=400, detail="action 必须是 add/update/remove")


@router.post("/portfolio/clear")
def clear_holdings():
    """清空所有持仓（测试用）。"""
    from agents.secretary_agent import load_portfolio, save_portfolio
    p = load_portfolio()
    p["holdings"] = []
    save_portfolio(p)
    return {"ok": True}


class HoldingUpdateBody(BaseModel):
    symbol: str
    account: str
    new_symbol: Optional[str] = None
    quantity: Optional[float] = None
    cost_price: Optional[float] = None
    currency: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    name: Optional[str] = None


class AccountUpdateBody(BaseModel):
    name: Optional[str] = None
    base_currency: Optional[str] = None
    broker: Optional[str] = None
    account_type: Optional[str] = None
    balance: Optional[float] = None


@router.patch("/portfolio/holdings")
def update_holding(body: HoldingUpdateBody):
    """行级编辑：更新单条持仓的 quantity、cost_price、currency、exchange 等。支持 new_symbol 替换标的。"""
    from agents.secretary_agent import update_holding as _update_holding
    from fastapi import HTTPException
    payload = body.model_dump(exclude_none=True)
    symbol = payload.pop("symbol", "").strip()
    account = payload.pop("account", "默认").strip() or "默认"
    new_symbol = (payload.pop("new_symbol", "") or "").strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol 必填")
    if "currency" in payload and payload.get("currency") not in ("CNY", "USD", "HKD"):
        payload.pop("currency", None)
    updated = _update_holding(symbol, account, new_symbol=new_symbol or None, **payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="未找到该持仓")
    return {"ok": True, "holding": updated}


@router.patch("/portfolio/accounts/{account_id}")
def update_account(account_id: str, body: AccountUpdateBody):
    """更新账户：name, base_currency, broker, account_type, balance。若账户不在 accounts 中则创建（upsert）。"""
    from agents.secretary_agent import update_account as _update_account, upsert_account
    payload = body.model_dump(exclude_none=True)
    acc = _update_account(account_id, **payload)
    if acc is None:
        # 账户可能仅存在于 holdings 中，upsert 创建到 accounts
        name = (payload.get("name") or account_id).strip() or account_id
        currency = (payload.get("base_currency") or "CNY").strip().upper()
        broker = (payload.get("broker") or "").strip()
        account_type = (payload.get("account_type") or "股票").strip()
        balance = payload.get("balance")
        acc = upsert_account(name, broker=broker, currency=currency, account_type=account_type, balance=balance)
    return {"ok": True, "account": acc}


@router.delete("/portfolio/accounts/{account_id}")
def delete_account(account_id: str):
    """删除账户：该账户下持仓迁移至「默认」。「默认」账户不可删除。"""
    from agents.secretary_agent import delete_account as _delete_account
    ok = _delete_account(account_id)
    if not ok:
        raise HTTPException(status_code=400, detail="无法删除该账户（可能为「默认」或不存在）")
    return {"ok": True}


@router.post("/portfolio/file/parse")
def parse_file(req: ParseFileRequest):
    """解析 CSV/JSON 文件，返回解析结果。contents 为 base64 编码。"""
    contents = req.contents
    filename = req.filename or ""
    if not contents:
        return {"status": "error", "error": "无文件内容"}
    try:
        import base64
        from agents.secretary_agent import parse_csv_holdings, parse_json_holdings, parse_excel_holdings
        if filename.lower().endswith(".xlsx"):
            excel_bytes = base64.b64decode(contents)
            holdings = parse_excel_holdings(excel_bytes)
        elif filename.lower().endswith(".xls"):
            return {"status": "error", "error": "暂不支持 .xls 格式，请另存为 .xlsx 后上传"}
        elif filename.lower().endswith(".csv"):
            raw = base64.b64decode(contents).decode("utf-8", errors="replace")
            holdings = parse_csv_holdings(raw)
        else:
            raw = base64.b64decode(contents).decode("utf-8", errors="replace")
            holdings = parse_json_holdings(raw)
        if not holdings:
            return {"status": "error", "error": "未解析到有效数据"}
        return {"status": "ok", "holdings": holdings}
    except Exception as e:
        return {"status": "error", "error": str(e)}
