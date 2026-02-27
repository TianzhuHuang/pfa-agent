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
    """Call Qwen API with conversation history."""
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
    from agents.secretary_agent import parse_csv_holdings, parse_json_holdings
    import pandas as pd

    if not callable(save_holdings):
        return False

    st.markdown('<div class="pfa-caption" style="margin-bottom:8px;">快捷录入</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    did_add = False

    with c1:
        with st.expander("📸 截图", expanded=False):
            img = st.file_uploader("上传券商截图", type=["png", "jpg", "jpeg", "webp"], key="qe_img")
            if img:
                ib = img.getvalue()
                if st.button("识别并导入", type="primary", key="qe_ocr"):
                    with st.spinner("识别中..."):
                        r = extract_holdings_from_image(ib, img.type or "image/png")
                    if r.get("status") == "ok" and r.get("holdings"):
                        save_holdings([{**x, "source": "ocr"} for x in r["holdings"]])
                        st.session_state["pfa_rerun_after_add"] = True
                        st.success(f"已录入 {len(r['holdings'])} 条")
                        did_add = True
                    else:
                        st.error(r.get("error", "识别失败"))

    with c2:
        with st.expander("📄 文件", expanded=False):
            up = st.file_uploader("CSV/JSON", type=["csv", "json"], key="qe_file")
            if up:
                raw = up.read().decode("utf-8")
                try:
                    parsed = parse_csv_holdings(raw) if up.name.endswith(".csv") else parse_json_holdings(raw)
                    if parsed and st.button("导入", type="primary", key="qe_import"):
                        save_holdings(parsed)
                        st.session_state["pfa_rerun_after_add"] = True
                        st.success(f"已导入 {len(parsed)} 条")
                        did_add = True
                except Exception as e:
                    st.error(str(e))

    with c3:
        with st.expander("🔍 搜索", expanded=False):
            q = st.text_input("股票名/代码", key="qe_search")
            if q and len(q.strip()) >= 1:
                for idx, r in enumerate((search_stock(q) or [])[:5]):
                    ca, cb = st.columns([3, 1])
                    ca.caption(f"{r['code']} {r['name']}")
                    if cb.button("添加", key=f"qe_add_{idx}_{r['code']}", type="primary"):
                        save_holdings([{"symbol": r["code"], "name": r["name"], "market": r.get("market", "A"), "source": "search"}])
                        st.session_state["pfa_rerun_after_add"] = True
                        did_add = True
                        st.rerun()

    return did_add


def render_expert_chat(
    holdings: List[Dict],
    val: Dict,
    user: Optional[Dict] = None,
    save_holdings: Optional[Any] = None,
    is_empty_state: bool = False,
):
    """Render the AI Expert chat panel：气泡对话、持久化、确认卡、输入区带 + 。"""
    from pfa.data.store import load_chat_history, save_chat_history

    user_id = (user or {}).get("user_id") or "admin"

    # 刚点击「确认」后的执行：执行 payload 并追加结果消息，再 rerun
    if "pfa_confirm_payload" in st.session_state:
        payload = st.session_state.pop("pfa_confirm_payload", None)
        if payload and "expert_chat" in st.session_state:
            reply = _execute_trade_payload(payload.get("parsed", {}), payload.get("user_input", ""))
            st.session_state["expert_chat"].append({"role": "assistant", "content": reply})
            save_chat_history(st.session_state["expert_chat"], user_id)
            st.session_state["pfa_rerun_after_add"] = True
        st.rerun()

    # 初始化对话：优先从持久化加载，否则迎宾
    if "expert_chat" not in st.session_state:
        stored = load_chat_history(user_id)
        if stored:
            st.session_state["expert_chat"] = stored
        else:
            if is_empty_state or (val.get("holding_count", 0) == 0 and not holdings):
                welcome = (
                    "👋 **你好！我是你的 AI 理财助理。**\n\n"
                    "把你的**持仓截图**丢给我，或者直接告诉我「我买了 100 股苹果」，我来帮你建账。\n\n"
                    "👇 你也可以用下方「快捷录入」上传截图、导入文件或搜索添加标的。"
                )
            else:
                total_v = val.get("total_value_cny", 0)
                total_pnl = val.get("total_pnl_cny", 0)
                total_pct = val.get("total_pnl_pct", 0)
                sign = "+" if total_pnl >= 0 else ""
                welcome = (
                    f"你好，我是你的投研专家。\n\n"
                    f"你目前持有 **{val.get('holding_count', 0)}** 只标的，"
                    f"总资产 **¥{total_v:,.0f}**，"
                    f"今日收益 **{sign}¥{total_pnl:,.0f}** ({sign}{total_pct:.2f}%)。\n\n"
                    f"你可以问我：\n"
                    f"- 「分析一下我的持仓风险」\n"
                    f"- 「加仓 500 股中海油 价格 24」\n"
                    f"- 「茅台最近有什么消息」"
                )
            st.session_state["expert_chat"] = [{"role": "assistant", "content": welcome}]

    # AI 主动破冰：录入完成后若存在重仓（>30%），主动询问是否生成调仓建议
    if (
        st.session_state.get("pfa_rerun_after_add")
        and not st.session_state.get("pfa_icebreaker_sent")
        and not is_empty_state
        and val
    ):
        top_weight = 0
        top_name = ""
        for acct_data in val.get("by_account", {}).values():
            for h in acct_data.get("holdings", []):
                w = h.get("weight_pct") or 0
                if w > top_weight:
                    top_weight = w
                    top_name = h.get("name", "")
        if top_weight >= 30 and top_name:
            ice = (
                f"我看到你重仓了 **{top_name}**（{top_weight:.1f}%），"
                "虽然可能收益不错，但单一标的风险较高。需要我为你生成一份调仓建议吗？"
            )
            st.session_state["expert_chat"].append({"role": "assistant", "content": ice})
            save_chat_history(st.session_state["expert_chat"], user_id)
            st.session_state["pfa_icebreaker_sent"] = True
            st.rerun()

    desc = "基于持仓数据，调仓 / 分析 / 备忘" if not is_empty_state else "上传截图或对我说一句话，马上建账"
    st.markdown(f"""
<div class="expert-chat-panel">
    <div class="chat-panel-header">
        <span class="chat-panel-title">投研助理</span>
        <span class="chat-panel-badge"><span class="dot"></span>实时</span>
</div>
    <div class="chat-panel-desc">{desc}</div>
    <div class="chat-panel-body">""", unsafe_allow_html=True)

    # 固定高度对话区，气泡布局：AI 左 / 用户右（略微收窄高度，避免占满整列）
    chat_box = st.container(height=260)
    with chat_box:
        for idx, msg in enumerate(st.session_state["expert_chat"]):
            role = msg.get("role", "assistant")
            if msg.get("type") == "confirm_card":
                # 确认卡片：文案 + 确认/取消
                payload = msg.get("payload", {})
                parsed = payload.get("parsed", {})
                name = parsed.get("name", "")
                sym = parsed.get("symbol", "")
                action = parsed.get("action", "")
                qty = parsed.get("quantity", 0)
                price = parsed.get("price", 0)
                action_text = {"add": "买入", "update": "更新", "remove": "删除"}.get(action, action)
                content = msg.get("content", "")
                col_l, col_r = st.columns([0.85, 0.15])
                with col_l:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(content)
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("确认", type="primary", key=f"confirm_ok_{idx}_{sym}_{action}"):
                                st.session_state["pfa_confirm_payload"] = {"parsed": parsed, "user_input": payload.get("user_input", "")}
                                st.rerun()
                        with c2:
                            if st.button("取消", key=f"confirm_no_{idx}_{sym}_{action}"):
                                st.session_state["expert_chat"][idx] = {"role": "assistant", "content": "已取消操作。"}
                                save_chat_history(st.session_state["expert_chat"], user_id)
                                st.rerun()
            else:
                avatar = "🤖" if role == "assistant" else "👤"
                if role == "user":
                    st.markdown(f'<span class="chat-row chat-user" style="display:none"></span>', unsafe_allow_html=True)
                    with st.chat_message("user", avatar=avatar):
                        st.markdown(msg.get("content", ""))
                else:
                    st.markdown(f'<span class="chat-row chat-assistant" style="display:none"></span>', unsafe_allow_html=True)
                    with st.chat_message("assistant", avatar=avatar):
                        st.markdown(msg.get("content", ""))

    # 自动滚动到底部（平滑）
    st.markdown(
        """
<script>
setTimeout(function() {
  const root = window.parent.document.querySelector('.expert-chat-panel');
  if (!root) return;
  const blocks = root.querySelectorAll('[data-testid="stVerticalBlock"]');
  if (!blocks.length) return;
  const box = blocks[blocks.length - 1];
  box.style.scrollBehavior = 'smooth';
  box.scrollTop = box.scrollHeight;
}, 10);
</script>
""",
        unsafe_allow_html=True,
    )

    # 快捷建议（Quick Actions）：始终常驻在输入框上方
    preset_query: Optional[str] = None
    if not is_empty_state:
        st.markdown('<div class="quick-actions-row">', unsafe_allow_html=True)
        qa1, qa2, qa3 = st.columns(3)
        with qa1:
            if st.button("分析今日风险", key="qr_risk"):
                preset_query = "请结合我当前持仓，分析一下今天整体的风险点，并指出需要重点警惕的几只股票。"
        with qa2:
            if st.button("总结个股异动", key="qr_moves"):
                preset_query = "帮我总结一下今天持仓里涨跌幅最剧烈的几只股票，以及可能的原因。"
        with qa3:
            if st.button("生成调仓建议", key="qr_rebalance"):
                preset_query = "结合我当前的仓位结构，给出一份本周的调仓建议，并说明理由。"
        st.markdown('</div>', unsafe_allow_html=True)

    # 底部输入区：固定在投研助理卡片底部，而不是整页底部
    input_cols = st.columns([0.08, 0.72, 0.20])
    user_input = ""
    with input_cols[0]:
        if save_holdings:
            if hasattr(st, "popover"):
                with st.popover("➕", help="识别截图 / 导入文件 / 搜索股票"):
                    st.caption("快捷录入")
                    _render_quick_entry(save_holdings, user)
            else:
                show_quick = st.session_state.get("pfa_show_quick_entry", False)
                if show_quick:
                    _render_quick_entry(save_holdings, user)
                if st.button("➕", key="chat_plus_btn", help="上传截图 / 导入文件 / 搜索股票"):
                    st.session_state["pfa_show_quick_entry"] = not st.session_state.get("pfa_show_quick_entry", False)
                    st.rerun()
    with input_cols[1]:
        user_text = st.text_input(
            "和投研专家对话...",
            key="expert_query",
            label_visibility="collapsed",
            placeholder="和投研专家对话...",
        )
    with input_cols[2]:
        send_clicked = st.button("发送", key="expert_send", type="primary")

    st.markdown("</div></div>", unsafe_allow_html=True)

    # 发送逻辑：优先使用快捷建议，其次使用输入框内容
    if preset_query:
        user_input = preset_query
    elif send_clicked and user_text.strip():
        user_input = user_text.strip()

    if user_input:
        st.session_state["expert_chat"].append({"role": "user", "content": user_input})

        parsed = _parse_trade_command(user_input)
        if parsed and parsed.get("action") in ("add", "update", "remove"):
            # 调仓类：先出确认卡，不直接执行
            action = parsed.get("action", "")
            name = parsed.get("name", "")
            sym = parsed.get("symbol", "")
            qty = parsed.get("quantity", 0)
            price = parsed.get("price", 0)
            action_cn = {"add": "买入", "update": "更新", "remove": "删除"}.get(action, action)
            if action == "add":
                content = f"将为您**{action_cn}**：**{name}**（{sym}）{qty}股" + (f" @{price}" if price else "") + "。确认执行？"
            elif action == "remove":
                content = f"将为您**{action_cn}**：**{name}**（{sym}）。确认执行？"
            else:
                content = f"将为您**{action_cn}**：**{name}**（{sym}）→ 数量 {qty}" + (f" @{price}" if price else "") + "。确认执行？"
            st.session_state["expert_chat"].append({
                "role": "assistant",
                "content": content,
                "type": "confirm_card",
                "payload": {"parsed": parsed, "user_input": user_input},
            })
        elif parsed and parsed.get("action") == "memo":
            reply = _execute_trade_payload(parsed, user_input)
            st.session_state["expert_chat"].append({"role": "assistant", "content": reply})
        elif parsed:
            reply = _execute_trade_payload(parsed, user_input)
            st.session_state["expert_chat"].append({"role": "assistant", "content": reply})
        else:
            system_prompt = _build_system_prompt(holdings, val)
            messages = [{"role": "system", "content": system_prompt}]
            for m in st.session_state["expert_chat"][-8:]:
                messages.append({"role": m["role"], "content": m.get("content", "")})
            with st.status("正在分析你的持仓与风险...", expanded=False) as status:
                reply = _call_ai(messages)
                status.update(label="分析完成", state="complete", expanded=False)
        st.session_state["expert_chat"].append({"role": "assistant", "content": reply})

        save_chat_history(st.session_state["expert_chat"], user_id)
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
