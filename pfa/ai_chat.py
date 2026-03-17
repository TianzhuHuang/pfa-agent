"""
AI Chat 逻辑 — 与 Streamlit 无关的纯函数

供 app/ai_expert.py 与 app_dash 共用。
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests

CST = timezone(timedelta(hours=8))
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

SYSTEM_PERSONA = """你是 PFA 投研专家，一位资深股票策略分析师。

你的特点：
- 专业且克制，不做过度承诺
- 基于数据和事实分析，不猜测
- 回答简洁有力，重点突出
- 了解 A 股、港股、美股市场
- 能识别用户的调仓指令并执行

用户当前持仓概况：
{portfolio_context}

回答规则：
- 使用中文
- 金额用 ¥ 符号 + 千分位
- 涨跌用 A 股惯例（红涨绿跌）
- 如果用户询问某只个股，结合持仓数据分析

输出格式（必须严格遵守）：
- 严禁输出超过 3 行的长句而不进行物理换行
- 段落之间、列表之后必须插入双换行符 \n\n
- 多使用 Markdown 二级标题 (##) 和水平分割线 (---) 增加内容结构化
- 重点词汇用 **加粗**，列表用 - 或 1. 有序列表"""


def build_system_prompt(holdings: List[Dict], val: Dict) -> str:
    """Build system prompt with portfolio context."""
    total_v = val.get("total_value_cny") or 0
    total_pnl = val.get("total_pnl_cny") or 0
    total_pct = val.get("total_pnl_pct") or 0
    sign = "+" if (total_pnl or 0) >= 0 else ""

    top_holdings = []
    for acct_data in val.get("by_account", {}).values():
        for h in acct_data.get("holdings", []):
            pnl_cny = h.get("pnl_cny")
            pnl_pct = h.get("pnl_pct")
            if pnl_cny is None:
                pnl_cny = 0
            if pnl_pct is None:
                pnl_pct = 0
            top_holdings.append({
                "代码": h["symbol"],
                "名称": h.get("name", ""),
                "现价": h.get("current_price", ""),
                "成本": h.get("cost_price", ""),
                "数量": h.get("quantity", ""),
                "盈亏": f"{'+' if pnl_cny >= 0 else ''}{pnl_cny:,.0f}",
                "涨跌": f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%",
            })

    context = (
        f"总资产: ¥{total_v:,.0f}\n"
        f"总收益: {sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)\n"
        f"持仓数: {val.get('holding_count', 0)} 只, {val.get('account_count', 0)} 个账户\n\n"
        f"持仓明细:\n{json.dumps(top_holdings, ensure_ascii=False, indent=2)}"
    )

    return SYSTEM_PERSONA.format(portfolio_context=context)


def call_ai_stream(messages: List[Dict]) -> Generator[str, None, None]:
    """Stream Qwen API response. Yields str chunks; on error yields error message."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        yield "需要配置 DASHSCOPE_API_KEY"
        return
    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": messages, "temperature": 0.4, "max_tokens": 1500, "stream": True},
            timeout=120,
            stream=True,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.strip().startswith("data:"):
                continue
            data = line.strip()[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content") or ""
                if content:
                    yield content
            except Exception:
                pass
    except Exception as e:
        yield f"AI 服务暂不可用: {e}"


def generate_impact_card_from_text(user_text: str, assistant_text: str) -> Optional[Dict[str, Any]]:
    """Best-effort: summarize assistant output into a structured ImpactCard.

    This is a Phase-1 local feature to enable UI ImpactCard rendering without changing the main answer style.
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return None
    prompt = f"""你是投研分析师。请把下面的回答提炼成一张“影响评估卡片”。\n\n用户问题：\n{user_text}\n\n助手回答：\n{assistant_text}\n\n请严格只输出 JSON（不要 markdown 代码块，不要额外文字），格式如下：\n{{\n  \"title\": \"一句话标题\",\n  \"summary\": \"2-4 句总结（可换行）\",\n  \"impacts\": [\n    {{\"symbol\": \"代码或BTC/ETH\", \"name\": \"名称\", \"level\": \"high|medium|low\", \"levelLabel\": \"高|中|低\", \"sentiment\": \"positive|negative|neutral\"}}\n  ]\n}}\n\n要求：\n- impacts 最多 5 条\n- 如果无法识别具体标的，就返回空数组 impacts=[]\n- levelLabel 用中文单字：高/中/低\n"""
    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 500},
            timeout=30,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        content = content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        impacts = data.get("impacts", [])
        if impacts is None:
            impacts = []
        if not isinstance(impacts, list):
            impacts = []
        data["impacts"] = impacts[:5]
        return data
    except Exception:
        return None


def _is_valid_symbol(s: str) -> bool:
    """股票代码需含数字或为常见格式，纯中文单字如「你」视为无效。"""
    s = (s or "").strip()
    if not s or len(s) < 2:
        return False
    # 含数字（A股/港股/美股代码）或全英文（如 AAPL）
    if any(c.isdigit() for c in s):
        return True
    if s.isalpha() and len(s) >= 2:
        return True
    return False


def parse_trade_command(user_input: str) -> Optional[Dict[str, Any]]:
    """Parse trade command; returns parsed dict or None."""
    from pfa.ai_portfolio_assistant import parse_portfolio_command

    parsed = parse_portfolio_command(user_input)
    if not parsed or parsed.get("error"):
        return None
    conf = parsed.get("confidence", 0)
    if isinstance(conf, (int, float)) and conf < 60:
        return None
    action = parsed.get("action", "")
    sym = str(parsed.get("symbol", "") or "").strip()
    name = str(parsed.get("name", "") or "").strip()
    # 若仅有名称无代码，尝试搜索补全
    if action in ("add", "remove", "update") and not _is_valid_symbol(sym) and name:
        sym = _resolve_symbol_from_name(name)
        if sym:
            parsed = dict(parsed)
            parsed["symbol"] = sym
    if action in ("add", "remove", "update", "memo") and not _is_valid_symbol(sym):
        return None
    return parsed


def _resolve_symbol_from_name(name: str) -> Optional[str]:
    """根据股票名称搜索补全代码。"""
    try:
        from pfa.stock_search import search_stock
        results = search_stock(name.strip(), count=1)
        if results:
            return str(results[0].get("code", "") or "").strip() or None
    except Exception:
        pass
    return None


def check_trade_completeness(parsed: Dict[str, Any]) -> Tuple[bool, List[str], str]:
    """校验交易信息是否完整。add 必须含 account 和 price；update/remove 需 account（多账户时）。

    Returns:
        (is_complete, missing_fields, clarify_message)
    """
    action = parsed.get("action", "")
    missing: List[str] = []
    if action == "add":
        account = str(parsed.get("account", "") or "").strip()
        price = float(parsed.get("price", 0) or 0)
        if not account:
            missing.append("account")
        if price <= 0:
            missing.append("price")
    elif action in ("update", "remove"):
        # 若持仓有多账户，需指定 account；单账户可默认
        account = str(parsed.get("account", "") or "").strip()
        # 暂不强制 account，默认用「默认」
        pass

    if not missing:
        return True, [], ""

    action_label = {"add": "买入", "update": "更新", "remove": "卖出"}.get(action, action)
    parts = []
    if "account" in missing:
        parts.append("要记录在哪个账户（如：观察仓、默认、数字货币）？")
    if "price" in missing:
        parts.append("成交均价是多少？")
    msg = f"好的，已识别{action_label}意图。请问：" + " ".join(parts)
    return False, missing, msg


def merge_trade_from_followup(user_input: str, pending: Dict[str, Any]) -> Dict[str, Any]:
    """将用户补全输入与 pending 合并。从「观察仓 25」「默认账户 价格25」等提取 account、price。"""
    import re
    merged = dict(pending)
    text = (user_input or "").strip()

    # 价格：数字（可含小数点）
    price_match = re.search(r"(?:价格?|成本|@|单价)\s*[:：]?\s*([\d.]+)", text, re.I)
    if not price_match:
        price_match = re.search(r"(\d+\.?\d*)\s*(?:块|元|块钱)", text)
    if not price_match:
        # 末尾独立数字可能是价格
        price_match = re.search(r"\s+([\d.]+)\s*$", text)
    if price_match:
        try:
            merged["price"] = float(price_match.group(1))
        except (ValueError, TypeError):
            pass

    # 账户：常见模式
    account_match = re.search(
        r"(?:账户|记录在|放到|存入)\s*[:：]?\s*([^\s\d,，.。]+)",
        text,
    )
    if account_match:
        merged["account"] = account_match.group(1).strip()
    else:
        # 排除纯数字后的词可能是账户名
        words = re.split(r"[\s,，]+", text)
        for w in words:
            w = w.strip()
            if w and not re.match(r"^[\d.]+$", w) and len(w) >= 2:
                merged["account"] = w
                break

    return merged


def execute_trade_payload(parsed: Dict[str, Any], user_input: str) -> str:
    """Execute a parsed trade (add/update/remove/memo). Returns reply text."""
    from agents.secretary_agent import load_portfolio, save_portfolio, add_memo

    action = parsed.get("action", "")
    sym = parsed.get("symbol", "")
    name = parsed.get("name", "")
    qty = parsed.get("quantity") if parsed.get("quantity") is not None else 0
    price = parsed.get("price") if parsed.get("price") is not None else 0
    now_str = datetime.now(CST).isoformat()
    p = load_portfolio()

    if action == "add":
        entry = {"symbol": sym, "name": name, "market": parsed.get("market", "A"), "source": "ai_expert", "updated_at": now_str}
        if qty > 0:
            entry["quantity"] = qty
        if price > 0:
            entry["cost_price"] = price
        p.setdefault("holdings", []).append(entry)
        save_portfolio(p)
        return f"✅ 已买入 **{name}**({sym}) {qty}股" + (f" @{price}" if price else "")

    elif action == "update":
        for h in p.get("holdings", []):
            if h["symbol"] == sym:
                if qty is not None and qty >= 0:
                    h["quantity"] = qty
                if price is not None and price > 0:
                    h["cost_price"] = price
                h["updated_at"] = now_str
                save_portfolio(p)
                return f"✅ 已更新 **{name}**({sym}) → 数量 {qty}" + (f" @{price}" if price else "")
        return f"⚠️ 未找到 {name}({sym})"

    elif action == "remove":
        before = len(p.get("holdings", []))
        p["holdings"] = [h for h in p.get("holdings", []) if h["symbol"] != sym]
        if len(p["holdings"]) < before:
            save_portfolio(p)
            return f"✅ 已删除 **{name}**({sym})"
        return f"⚠️ 未找到 {name}({sym})"

    elif action == "memo":
        ok = add_memo(sym, parsed.get("memo_action", "note"), parsed.get("text", user_input))
        return f"📝 已记录 **{name}**({sym}) 备忘" if ok else f"⚠️ 未找到 {name}({sym})"

    return ""


def build_welcome_message(val: Dict) -> str:
    """Build initial welcome message for empty chat."""
    total_v = val.get("total_value_cny") or 0
    total_pnl = val.get("total_pnl_cny") or 0
    total_pct = val.get("total_pnl_pct") or 0
    sign = "+" if (total_pnl or 0) >= 0 else ""
    return (
        f"👋 你好，我是你的 AI 投研助理。\n\n"
        f"当前总资产 **¥{total_v:,.0f}**，"
        f"累计收益 **{sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)**。\n\n"
        f"你可以问我：\n"
        f"- 「分析一下我的持仓风险」\n"
        f"- 「帮我看下今天有哪些异动」\n"
        f"- 「基于最近新闻，给我一份调仓建议」"
    )
