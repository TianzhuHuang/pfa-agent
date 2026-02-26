"""
PFA v2 — 主入口

流程:
  未登录 → 居中登录页
  已登录 + 无持仓 → 引导录入页
  已登录 + 有持仓 → Portfolio Hub (总资产 + 持仓 + AI Chat)

顶部导航: Portfolio | Briefing | Analysis | Settings
侧边栏: 隐藏
"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="PFA 投研助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from app.theme_v2 import inject_v2_theme, render_topnav
from app.auth_v2 import get_user, render_login_page

inject_v2_theme()

# --- Auth gate ---
user = get_user()

if not user.get("user_id"):
    render_login_page()
    st.stop()

# --- Logged in: render top nav + hub ---
render_topnav(active="portfolio", user_email=user.get("email", ""))

# --- Check if portfolio is empty → onboarding ---
from agents.secretary_agent import load_portfolio
portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

if not holdings:
    # Empty state — onboarding
    st.markdown("""
<div class="empty-state">
    <div class="icon">📊</div>
    <div class="title">欢迎使用 PFA 投研助手</div>
    <div>添加你的第一笔持仓，开始智能投研之旅</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""<div class="onboard-card" style="text-align:center;">
<div style="font-size:32px; margin-bottom:8px;">🔍</div>
<div style="font-weight:600; margin-bottom:4px;">智能搜索</div>
<div style="color:#999; font-size:13px;">输入代码或名称快速添加</div>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""<div class="onboard-card" style="text-align:center;">
<div style="font-size:32px; margin-bottom:8px;">📸</div>
<div style="font-weight:600; margin-bottom:4px;">截图识别</div>
<div style="color:#999; font-size:13px;">上传券商截图 AI 自动提取</div>
</div>""", unsafe_allow_html=True)

    with col3:
        st.markdown("""<div class="onboard-card" style="text-align:center;">
<div style="font-size:32px; margin-bottom:8px;">📄</div>
<div style="font-weight:600; margin-bottom:4px;">文件导入</div>
<div style="color:#999; font-size:13px;">CSV / JSON 批量导入</div>
</div>""", unsafe_allow_html=True)

    # Quick add section
    st.markdown("### 开始添加持仓")
    from pfa.stock_search import search_stock
    from agents.secretary_agent import add_holding, save_portfolio
    from datetime import datetime, timedelta, timezone

    query = st.text_input("搜索股票", placeholder="输入代码或名称，如：茅台、00700、AAPL")
    if query and len(query.strip()) >= 1:
        results = search_stock(query)
        if results:
            for r in results[:5]:
                col_a, col_b = st.columns([4, 1])
                col_a.markdown(f"**{r['code']}** {r['name']} · {r['market_raw']}")
                if col_b.button("添加", key=f"add_{r['code']}"):
                    add_holding(r["code"], r["name"], r["market"], 0, 0, 0, "search")
                    st.rerun()

    st.stop()

# --- Has holdings: Portfolio Hub ---
from html import escape
from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices

# Fetch real-time data
fx = get_fx_rates()
prices = get_realtime_prices(holdings)
val = calculate_portfolio_value(holdings, prices, fx)

total_v = val["total_value_cny"]
total_pnl = val["total_pnl_cny"]
total_pct = val["total_pnl_pct"]
from app.theme_v2 import COLORS
pnl_color = COLORS["up"] if total_pnl >= 0 else COLORS["down"]
sign = "+" if total_pnl >= 0 else ""

# --- Top: Total Wealth ---
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"""<div class="metric-card">
<div class="label">Total Portfolio</div>
<div class="value">¥{total_v:,.0f}</div>
</div>""", unsafe_allow_html=True)

c2.markdown(f"""<div class="metric-card">
<div class="label">Total Return</div>
<div class="value" style="color:{pnl_color};">{sign}¥{total_pnl:,.0f}</div>
<div class="change" style="color:{pnl_color};">{sign}{total_pct:.2f}%</div>
</div>""", unsafe_allow_html=True)

c3.markdown(f"""<div class="metric-card">
<div class="label">Holdings</div>
<div class="value">{val['holding_count']}</div>
</div>""", unsafe_allow_html=True)

c4.markdown(f"""<div class="metric-card">
<div class="label">Accounts</div>
<div class="value">{val['account_count']}</div>
</div>""", unsafe_allow_html=True)

# --- Holdings Table + AI Chat (side by side) ---
st.markdown("---")
col_holdings, col_chat = st.columns([3, 2])

with col_holdings:
    st.markdown("### Holdings")

    # Build Sharesight-style table
    table_html = '<table class="fin-table"><thead><tr>'
    for col in ["Symbol", "Name", "Price", "Cost", "Qty", "Value", "Return", "%"]:
        align = "right" if col not in ["Symbol", "Name"] else ""
        table_html += f'<th class="{align}">{col}</th>'
    table_html += '</tr></thead><tbody>'

    for acct_name, acct_data in val["by_account"].items():
        # Account group header
        table_html += f'<tr><td colspan="8" style="padding:12px;font-weight:600;color:#999;font-size:12px;border-bottom:1px solid #E9ECEF;background:#FAFBFC;">{escape(acct_name)} · ¥{acct_data["value"]:,.0f}</td></tr>'

        for h in acct_data["holdings"]:
            pnl = h["pnl_cny"]
            pct = h["pnl_pct"]
            pnl_cls = "up" if pnl >= 0 else "down"
            ps = "+" if pnl >= 0 else ""

            table_html += '<tr>'
            table_html += f'<td><a class="sym" href="/?page=ticker&symbol={h["symbol"]}">{h["symbol"]}</a></td>'
            table_html += f'<td>{escape(h.get("name",""))}</td>'
            table_html += f'<td class="right">{h.get("current_price","—")}</td>'
            table_html += f'<td class="right" style="color:#999;">{h.get("cost_price","—")}</td>'
            table_html += f'<td class="right">{h.get("quantity","—")}</td>'
            table_html += f'<td class="right">¥{h["value_cny"]:,.0f}</td>'
            table_html += f'<td class="right {pnl_cls}">{ps}{pnl:,.0f}</td>'
            table_html += f'<td class="right {pnl_cls}">{ps}{pct:.1f}%</td>'
            table_html += '</tr>'

    table_html += '</tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)

with col_chat:
    st.markdown("### AI Expert")
    st.caption("基于你的持仓，向 AI 投研专家提问")

    if "expert_chat" not in st.session_state:
        # Generate context-aware welcome
        top3 = sorted(val.get("by_account", {}).values(),
                       key=lambda x: x["value"], reverse=True)
        st.session_state["expert_chat"] = [{
            "role": "assistant",
            "content": f"你好！我是你的投研专家。\n\n你目前持有 **{val['holding_count']}** 只标的，总资产 **¥{total_v:,.0f}**，"
                       f"今日收益 **{sign}¥{total_pnl:,.0f}** ({sign}{total_pct:.2f}%)。\n\n"
                       f"你可以问我：\n"
                       f"- 「分析一下我的持仓风险」\n"
                       f"- 「加仓 500 股中海油 价格 24」\n"
                       f"- 「茅台最近有什么利好消息」"
        }]

    chat_box = st.container(height=400)
    with chat_box:
        for msg in st.session_state["expert_chat"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("和 AI 专家对话...")

    if user_input:
        import os, json, requests
        st.session_state["expert_chat"].append({"role": "user", "content": user_input})

        # Check if it's a portfolio command
        from pfa.ai_portfolio_assistant import parse_portfolio_command
        parsed = parse_portfolio_command(user_input)

        if parsed.get("action") in ("add", "update", "remove", "memo") and parsed.get("confidence", 0) > 60:
            # Portfolio operation
            action = parsed["action"]
            sym = parsed.get("symbol", "")
            name = parsed.get("name", "")
            qty = parsed.get("quantity", 0)
            price = parsed.get("price", 0)
            CST = __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
            now_str = __import__("datetime").datetime.now(CST).isoformat()

            p = load_portfolio()

            if action == "add":
                entry = {"symbol": sym, "name": name, "market": parsed.get("market", "A"),
                         "source": "ai_expert", "updated_at": now_str}
                if qty > 0: entry["quantity"] = qty
                if price > 0: entry["cost_price"] = price
                p.setdefault("holdings", []).append(entry)
                save_portfolio(p)
                reply = f"✅ 已买入 **{name}**({sym}) {qty}股" + (f" @{price}" if price else "")

            elif action == "update":
                ok = False
                for h in p.get("holdings", []):
                    if h["symbol"] == sym:
                        if qty >= 0: h["quantity"] = qty
                        if price > 0: h["cost_price"] = price
                        h["updated_at"] = now_str
                        ok = True
                        break
                if ok:
                    save_portfolio(p)
                    reply = f"✅ 已更新 **{name}**({sym})"
                else:
                    reply = f"⚠️ 未找到 {name}({sym})"

            elif action == "remove":
                before = len(p.get("holdings", []))
                p["holdings"] = [h for h in p.get("holdings", []) if h["symbol"] != sym]
                if len(p["holdings"]) < before:
                    save_portfolio(p)
                    reply = f"✅ 已删除 **{name}**({sym})"
                else:
                    reply = f"⚠️ 未找到 {name}({sym})"

            elif action == "memo":
                from agents.secretary_agent import add_memo
                ok = add_memo(sym, parsed.get("memo_action", "note"), parsed.get("text", user_input))
                reply = f"📝 已记录 **{name}**({sym}) 备忘" if ok else f"⚠️ 未找到 {name}({sym})"
            else:
                reply = "❓ 未知操作"

        else:
            # General AI chat with portfolio context
            holdings_summary = json.dumps([{
                "symbol": h["symbol"], "name": h.get("name",""), "market": h.get("market",""),
                "cost": h.get("cost_price",0), "qty": h.get("quantity",0),
            } for h in holdings[:10]], ensure_ascii=False)

            prompt = (
                f"你是一位资深股票策略分析师，语气专业且克制。\n\n"
                f"用户的持仓概况：总资产 ¥{total_v:,.0f}，今日收益 {sign}¥{total_pnl:,.0f} ({sign}{total_pct:.2f}%)\n"
                f"持仓明细（前10）：{holdings_summary}\n\n"
                f"用户问题：{user_input}\n\n"
                f"请基于持仓数据给出专业分析，中文回答。"
            )

            api_key = os.environ.get("DASHSCOPE_API_KEY")
            if api_key:
                try:
                    resp = requests.post(
                        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": "qwen-plus",
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.4, "max_tokens": 1500},
                        timeout=60)
                    resp.raise_for_status()
                    reply = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    reply = f"分析失败: {e}"
            else:
                reply = "需要配置 DASHSCOPE_API_KEY"

        st.session_state["expert_chat"].append({"role": "assistant", "content": reply})
        st.rerun()
