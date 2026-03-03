"""
AI Expert Chat Module — 持仓感知的投研专家对话

功能:
  - 自动注入持仓上下文 (system prompt)
  - 对话内调仓 (buy/sell/update + 确认卡片)
  - 个股深度分析 (symbol click → chat analysis)
  - 持仓风险分析 (AI 主动发起)
  - 晨报/预警消息嵌入
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.theme_v2 import COLORS

CST = timezone(timedelta(hours=8))


def _pfa_avatar():
    """PFA 乌龟 Logo，用于 AI 回复头像。与顶栏 logo 一致。"""
    from app.theme_v2 import _logo_data_uri
    return _logo_data_uri()
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
- 如果用户询问某只个股，结合持仓数据分析"""


def _build_system_prompt(holdings: List[Dict], val: Dict) -> str:
    """Build system prompt with portfolio context."""
    total_v = val.get("total_value_cny", 0)
    total_pnl = val.get("total_pnl_cny", 0)
    total_pct = val.get("total_pnl_pct", 0)
    sign = "+" if total_pnl >= 0 else ""

    top_holdings = []
    for acct_data in val.get("by_account", {}).values():
        for h in acct_data.get("holdings", []):
            top_holdings.append({
                "代码": h["symbol"],
                "名称": h.get("name", ""),
                "现价": h.get("current_price", ""),
                "成本": h.get("cost_price", ""),
                "数量": h.get("quantity", ""),
                "盈亏": f"{'+' if h['pnl_cny']>=0 else ''}{h['pnl_cny']:,.0f}",
                "涨跌": f"{'+' if h['pnl_pct']>=0 else ''}{h['pnl_pct']:.1f}%",
            })

    context = (
        f"总资产: ¥{total_v:,.0f}\n"
        f"总收益: {sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)\n"
        f"持仓数: {val.get('holding_count', 0)} 只, {val.get('account_count', 0)} 个账户\n\n"
        f"持仓明细:\n{json.dumps(top_holdings, ensure_ascii=False, indent=2)}"
    )

    return SYSTEM_PERSONA.format(portfolio_context=context)


def _call_ai(messages: List[Dict]) -> str:
    """Call Qwen API with conversation history (non-streaming)."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        return "需要配置 DASHSCOPE_API_KEY"
    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": messages,
                  "temperature": 0.4, "max_tokens": 1500},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI 服务暂不可用: {e}"


def _call_ai_stream(messages: List[Dict]):
    """Stream Qwen API response for st.write_stream. Yields str chunks; on error yields nothing and caller should use toast."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        yield "需要配置 DASHSCOPE_API_KEY"
        return
    try:
        resp = requests.post(
            DASHSCOPE_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": messages,
                  "temperature": 0.4, "max_tokens": 1500, "stream": True},
            timeout=60,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.strip().startswith("data:"):
                continue
            data = line.strip()[5:].strip()
            if data == "[DONE]":
                break
            try:
                import json as _json
                obj = _json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content") or ""
                if content:
                    yield content
            except Exception:
                pass
    except Exception as e:
        yield f"AI 服务暂不可用: {e}"


def _parse_trade_command(user_input: str) -> Optional[Dict[str, Any]]:
    """Only parse; returns parsed dict or None. Used for confirm card flow."""
    from pfa.ai_portfolio_assistant import parse_portfolio_command
    parsed = parse_portfolio_command(user_input)
    if not parsed or parsed.get("confidence", 0) < 60:
        return None
    return parsed


def _execute_trade_payload(parsed: Dict[str, Any], user_input: str) -> str:
    """Execute a parsed trade (add/update/remove/memo). Returns reply text."""
    from agents.secretary_agent import load_portfolio, save_portfolio, add_memo
    action = parsed.get("action", "")
    sym = parsed.get("symbol", "")
    name = parsed.get("name", "")
    qty = parsed.get("quantity", 0)
    price = parsed.get("price", 0)
    now_str = datetime.now(CST).isoformat()
    p = load_portfolio()

    if action == "add":
        entry = {"symbol": sym, "name": name, "market": parsed.get("market", "A"),
                 "source": "ai_expert", "updated_at": now_str}
        if qty > 0: entry["quantity"] = qty
        if price > 0: entry["cost_price"] = price
        p.setdefault("holdings", []).append(entry)
        save_portfolio(p)
        return f"✅ 已买入 **{name}**({sym}) {qty}股" + (f" @{price}" if price else "")

    elif action == "update":
        for h in p.get("holdings", []):
            if h["symbol"] == sym:
                if qty >= 0: h["quantity"] = qty
                if price > 0: h["cost_price"] = price
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


def _handle_trade_command(user_input: str, holdings: List[Dict], user: Optional[Dict] = None) -> Optional[str]:
    """Execute trade immediately (legacy path). For confirm flow use _parse_trade_command + _execute_trade_payload."""
    parsed = _parse_trade_command(user_input)
    if not parsed:
        return None
    return _execute_trade_payload(parsed, user_input)


def _render_quick_entry(save_holdings, user) -> bool:
    """在输入框上方渲染「上传截图 / 导入文件 / 搜索股票」，成功写入后返回 True 便于调用方 rerun。"""
    from pfa.screenshot_ocr import extract_holdings_from_image
    from pfa.stock_search import search_stock
    # 兼容旧版本：get_accounts / upsert_account 可能尚未存在时回退到简化逻辑
    try:
        from agents.secretary_agent import (  # type: ignore
            parse_csv_holdings,
            parse_json_holdings,
            load_portfolio,
            get_accounts,
            upsert_account,
        )
    except ImportError:
        from agents.secretary_agent import (  # type: ignore
            parse_csv_holdings,
            parse_json_holdings,
            load_portfolio,
        )

        def get_accounts() -> list:  # type: ignore
            return []

        def upsert_account(name: str, broker: str = "", currency: str = "CNY") -> dict:  # type: ignore
            return {"id": name, "name": name, "broker": broker, "currency": currency}

    if not callable(save_holdings):
        return False

    # 账户选择（所有导入方式共享）：先问「导入到哪个账户？」
    portfolio = load_portfolio()
    accounts = get_accounts()
    labels = []
    name_by_label = {}
    if accounts:
        for acc in accounts:
            nm = acc.get("name", "").strip() or "未命名账户"
            broker = acc.get("broker", "").strip()
            ccy = acc.get("currency", "CNY").strip().upper()
            meta = []
            if broker:
                meta.append(broker)
            if ccy:
                meta.append(ccy)
            label = f"{nm}（{' · '.join(meta)}）" if meta else nm
            labels.append(label)
            name_by_label[label] = nm
    else:
        # 兼容旧数据：从现有持仓里的 account 值推断账户名
        existing_accounts = sorted(
            {str(h.get("account", "")).strip() for h in portfolio.get("holdings", []) if h.get("account")}
        )
        labels = existing_accounts or ["默认账户"]
        name_by_label = {lb: lb for lb in labels}

    st.markdown(
        "<div class='pfa-caption' style='margin-bottom:8px;font-size:12px;font-weight:600;color:#5F6368;text-transform:uppercase;letter-spacing:0.5px;'>选择导入账户</div>",
        unsafe_allow_html=True,
    )
    acct_options = labels + ["➕ 新建账户"]
    choice = st.radio(
        "持仓将归入哪个账户？",
        acct_options,
        key="qe_account_choice",
        horizontal=False,
    )
    target_account_name: str = ""
    if choice == "➕ 新建账户":
        new_acct = st.text_input("账户名称", key="qe_new_account_name", placeholder="例如：主账户 / 美股小号")
        broker = st.text_input("券商 / 平台", key="qe_new_account_broker", placeholder="可选，例如：富途 / 华泰")
        currency = st.selectbox(
            "计价货币",
            ["CNY", "HKD", "USD", "其他"],
            index=0,
            key="qe_new_account_ccy",
        )
        new_acct = (new_acct or "").strip()
        if new_acct:
            # 实时写入/更新账户元信息，后续导入记录只用 name 绑定
            upsert_account(new_acct, broker=broker, currency=currency)
            target_account_name = new_acct
    else:
        target_account_name = name_by_label.get(choice, "").strip()

    if not target_account_name:
        st.info("请先选择或输入账户（名称必填），然后再使用下方的录入方式。")
        return False

    # 录入方式采用纵向卡片/折叠区，避免在窄对话框中出现挤压、错位
    st.markdown(
        '<div class="pfa-caption" style="margin:16px 0 0;padding-top:12px;border-top:1px solid #2D3139;font-size:12px;font-weight:600;color:#5F6368;text-transform:uppercase;letter-spacing:0.5px;">快捷录入</div>',
        unsafe_allow_html=True,
    )
    did_add = False

    # 1) 从截图识别
    with st.expander("📸 从截图识别", expanded=False):
        img = st.file_uploader("上传券商截图", type=["png", "jpg", "jpeg", "webp"], key="qe_img")
        if img:
            ib = img.getvalue()
            if st.button("识别生成清单", type="primary", key="qe_ocr"):
                with st.spinner("识别中..."):
                    r = extract_holdings_from_image(ib, img.type or "image/png")
                if r.get("status") == "ok" and r.get("holdings"):
                    # 先写入待确认列表，供下方预览编辑
                    pending = []
                    for x in r["holdings"]:
                        item = {**x, "source": "ocr"}
                        if not item.get("account"):
                            item["account"] = target_account_name
                        pending.append(item)
                    st.session_state["qe_pending_ocr"] = pending
                    st.success(f"已识别 {len(r['holdings'])} 条，请在下方确认后再导入。")
                else:
                    st.error(r.get("error", "识别失败"))
        # 预览 & 确认导入
        if "qe_pending_ocr" in st.session_state:
            import pandas as pd

            df = pd.DataFrame(st.session_state["qe_pending_ocr"])
            if "account" not in df.columns:
                df["account"] = target_account_name
            st.markdown('<div class="pfa-caption" style="margin-bottom:8px;font-size:12px;color:#9AA0A6;">预览并可在导入前微调</div>', unsafe_allow_html=True)
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="qe_ocr_preview",
            )
            summary = f"即将导入 {len(edited)} 条持仓，账户：{target_account_name}"
            st.markdown(f'<div class="pfa-caption" style="margin-top:8px;font-size:12px;color:#9AA0A6;">{summary}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("确认导入", type="primary", key="qe_ocr_confirm"):
                    records = edited.to_dict("records")
                    save_holdings(records)
                    st.session_state["pfa_rerun_after_add"] = True
                    did_add = True
                    del st.session_state["qe_pending_ocr"]
                    st.session_state["open_holdings_entry"] = False  # 关闭录入持仓浮窗
                    st.rerun()
            with c2:
                if st.button("取消", key="qe_ocr_cancel"):
                    del st.session_state["qe_pending_ocr"]

    # 2) 从文件导入
    with st.expander("📄 从文件导入 (CSV/JSON)", expanded=False):
        up = st.file_uploader("上传 CSV 或 JSON 文件", type=["csv", "json"], key="qe_file")
        if up:
            raw = up.read().decode("utf-8")
            try:
                parsed = parse_csv_holdings(raw) if up.name.endswith(".csv") else parse_json_holdings(raw)
                if parsed and st.button("生成预览", type="primary", key="qe_import"):
                    pending = []
                    for h in parsed:
                        item = dict(h)
                        if not item.get("account"):
                            item["account"] = target_account_name
                        pending.append(item)
                    st.session_state["qe_pending_file"] = pending
                    st.success(f"已解析 {len(parsed)} 条，请在下方确认后再导入。")
            except Exception as e:
                st.error(str(e))
        # 预览 & 确认导入
        if "qe_pending_file" in st.session_state:
            import pandas as pd

            df = pd.DataFrame(st.session_state["qe_pending_file"])
            if "account" not in df.columns:
                df["account"] = target_account_name
            st.markdown('<div class="pfa-caption" style="margin-bottom:8px;font-size:12px;color:#9AA0A6;">预览并可在导入前微调</div>', unsafe_allow_html=True)
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="qe_file_preview",
            )
            acct_set = sorted({str(r.get("account", "")).strip() for _, r in edited.iterrows() if r.get("account")})
            summary = f"即将导入 {len(edited)} 条持仓，涉及账户：{', '.join(acct_set) or target_account_name}"
            st.markdown(f'<div class="pfa-caption" style="margin-top:8px;font-size:12px;color:#9AA0A6;">{summary}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("确认导入", type="primary", key="qe_file_confirm"):
                    records = edited.to_dict("records")
                    save_holdings(records)
                    st.session_state["pfa_rerun_after_add"] = True
                    did_add = True
                    del st.session_state["qe_pending_file"]
                    st.session_state["open_holdings_entry"] = False  # 关闭录入持仓浮窗
                    st.rerun()
            with c2:
                if st.button("取消", key="qe_file_cancel"):
                    del st.session_state["qe_pending_file"]

    # 3) 搜索/输入代码
    with st.expander("🔍 搜索 / 输入代码", expanded=False):
        q = st.text_input("股票名/代码", key="qe_search")
        if q and len(q.strip()) >= 1:
            for idx, r in enumerate((search_stock(q) or [])[:5]):
                ca, cb = st.columns([3, 1])
                ca.markdown(f'<div class="pfa-caption" style="font-size:14px;color:#E8EAED;padding:8px 0;">{r["code"]} {r["name"]}</div>', unsafe_allow_html=True)
                if cb.button("添加", key=f"qe_add_{idx}_{r['code']}", type="primary"):
                    pending = st.session_state.get("qe_pending_search", [])
                    pending.append(
                        {
                            "symbol": r["code"],
                            "name": r["name"],
                            "market": r.get("market", "A"),
                            "source": "search",
                            "account": target_account_name,
                        }
                    )
                    st.session_state["qe_pending_search"] = pending

        # 预览 & 确认导入（搜索/手动添加）
        if "qe_pending_search" in st.session_state and st.session_state["qe_pending_search"]:
            import pandas as pd

            df = pd.DataFrame(st.session_state["qe_pending_search"])
            st.markdown('<div class="pfa-caption" style="margin-bottom:8px;font-size:12px;color:#9AA0A6;">待导入列表（可编辑）</div>', unsafe_allow_html=True)
            edited = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="qe_search_preview",
            )
            acct_set = sorted({str(r.get("account", "")).strip() for _, r in edited.iterrows() if r.get("account")})
            summary = f"即将导入 {len(edited)} 条持仓，涉及账户：{', '.join(acct_set) or target_account_name}"
            st.markdown(f'<div class="pfa-caption" style="margin-top:8px;font-size:12px;color:#9AA0A6;">{summary}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("确认导入", type="primary", key="qe_search_confirm"):
                    records = edited.to_dict("records")
                    save_holdings(records)
                    st.session_state["pfa_rerun_after_add"] = True
                    did_add = True
                    del st.session_state["qe_pending_search"]
                    st.session_state["open_holdings_entry"] = False  # 关闭录入持仓浮窗
                    st.rerun()
            with c2:
                if st.button("清空列表", key="qe_search_cancel"):
                    del st.session_state["qe_pending_search"]

    return did_add


def render_analysis_chat(
    holdings: List[Dict],
    val: Dict,
    user: Optional[Dict] = None,
) -> None:
    """Ask PFA 对话：深色主题、可滚动消息区、底部输入。样式由 theme_v2 统一管理。"""
    from pfa.data.store import load_chat_history, save_chat_history

    user_id = (user or {}).get("user_id") or "admin"

    if "analysis_chat" not in st.session_state:
        stored = load_chat_history(user_id)
        if stored:
            st.session_state["analysis_chat"] = stored
        else:
            total_v = val.get("total_value_cny", 0)
            total_pnl = val.get("total_pnl_cny", 0)
            total_pct = val.get("total_pnl_pct", 0)
            sign = "+" if total_pnl >= 0 else ""
            welcome = (
                f"👋 你好，我是你的 AI 投研助理。\n\n"
                f"当前总资产 **¥{total_v:,.0f}**，"
                f"累计收益 **{sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)**。\n\n"
                f"你可以问我：\n"
                f"- 「分析一下我的持仓风险」\n"
                f"- 「帮我看下今天有哪些异动」\n"
                f"- 「基于最近新闻，给我一份调仓建议」"
            )
            st.session_state["analysis_chat"] = [
                {"role": "assistant", "content": welcome}
            ]

    messages_state: List[Dict[str, Any]] = st.session_state["analysis_chat"]

    # 可滚动消息区
    chat_box = st.container(height=360)
    with chat_box:
        for msg in messages_state:
            role = msg.get("role", "assistant")
            avatar = _pfa_avatar() if role == "assistant" else None
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg.get("content", ""))

    # 底部输入区：参考截图 — 药丸与输入框同一视觉单元（样式由 theme_v2 管理）
    chips = [
        ("分析持仓", "分析一下我的持仓风险"),
        ("扫描风险", "帮我看下今天有哪些异动"),
        ("生成周报", "基于最近新闻，给我一份调仓建议"),
    ]
    chip_cols = st.columns(len(chips))
    for i, (label, prompt) in enumerate(chips):
        with chip_cols[i]:
            if st.button(label, key=f"pfa_chip_{i}", type="secondary", use_container_width=True):
                st.session_state["pfa_chip_trigger"] = prompt
                st.rerun()

    user_input = st.chat_input("问问投资的问题吧，帮你发现投资好机会")
    user_input = user_input or st.session_state.pop("pfa_chip_trigger", None)

    if user_input:
        messages_state.append({"role": "user", "content": user_input})

        parsed = _parse_trade_command(user_input)
        reply = ""
        if parsed and parsed.get("action") in ("add", "update", "remove", "memo") and parsed.get("symbol"):
            reply = _execute_trade_payload(parsed, user_input)
        else:
            system_prompt = _build_system_prompt(holdings, val)
            api_messages = [{"role": "system", "content": system_prompt}]
            for m in messages_state[-8:]:
                api_messages.append({"role": m["role"], "content": m.get("content", "")})

            gen = _call_ai_stream(api_messages)
            first = next(gen, "")
            if first and (
                first.strip().startswith("需要配置 DASHSCOPE_API_KEY")
                or first.strip().startswith("AI 服务暂不可用")
            ):
                st.toast("当前未配置 DASHSCOPE_API_KEY 或服务异常，请检查配置后重试。", icon="⚠️")
            else:
                def _stream():
                    if first:
                        yield first
                    for chunk in gen:
                        yield chunk

                with st.chat_message("assistant", avatar=_pfa_avatar()):
                    reply = st.write_stream(_stream())

        if reply:
            messages_state.append({"role": "assistant", "content": reply})
        save_chat_history(messages_state, user_id)
        st.rerun()


def inject_morning_greeting(val: Dict):
    """Inject proactive morning analysis if first visit today."""
    today = datetime.now(CST).strftime("%Y-%m-%d")
    if st.session_state.get("last_greeting_date") == today:
        return

    total_v = val.get("total_value_cny", 0)
    total_pnl = val.get("total_pnl_cny", 0)
    total_pct = val.get("total_pnl_pct", 0)
    sign = "+" if total_pnl >= 0 else ""
    n = val.get("holding_count", 0)

    # Find top gainer/loser
    top_gain = {"name": "", "pct": 0}
    top_loss = {"name": "", "pct": 0}
    concentration_warning = ""

    for acct_data in val.get("by_account", {}).values():
        for h in acct_data.get("holdings", []):
            pct = h.get("pnl_pct", 0)
            weight = h.get("value_cny", 0) / total_v * 100 if total_v > 0 else 0
            if pct > top_gain["pct"]:
                top_gain = {"name": h.get("name", ""), "pct": pct}
            if pct < top_loss["pct"]:
                top_loss = {"name": h.get("name", ""), "pct": pct}
            if weight > 30 and not concentration_warning:
                concentration_warning = f"\n⚠️ **{h.get('name','')}** 仓位占 {weight:.0f}%，超过分散化建议线 30%"

    greeting = (
        f"☀️ 早上好！你的持仓概况：\n\n"
        f"📊 总资产 **¥{total_v:,.0f}** · {n} 只标的\n"
        f"💰 累计收益 **{sign}¥{total_pnl:,.0f}** ({sign}{total_pct:.1f}%)\n"
    )

    if top_gain["name"]:
        greeting += f"📈 最大盈利：{top_gain['name']} +{top_gain['pct']:.1f}%\n"
    if top_loss["name"]:
        greeting += f"📉 最大亏损：{top_loss['name']} {top_loss['pct']:.1f}%\n"

    if concentration_warning:
        greeting += concentration_warning + "\n"

    greeting += "\n你可以问我「分析持仓风险」或「生成今日晨报」"

    if "expert_chat" in st.session_state:
        st.session_state["expert_chat"].append({"role": "assistant", "content": greeting})

    st.session_state["last_greeting_date"] = today
