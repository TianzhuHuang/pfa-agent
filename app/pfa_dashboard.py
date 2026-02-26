"""
PFA v2 — Portfolio Hub

Flow:
  Not logged in → Login page
  No holdings → Onboarding
  Has holdings → Total Wealth + Holdings Table + AI Expert Chat
"""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="PFA", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user, render_login_page
from app.notifications import render_bell_icon

inject_v2_theme()

# --- Auth ---
user = get_user()
if not user.get("user_id"):
    render_login_page()
    st.stop()

# --- Top nav with notification bell ---
bell = render_bell_icon()
render_topnav(active="portfolio", user_email=user.get("email", ""))

# --- Load portfolio (Supabase for cloud users, local JSON for admin) ---
holdings = []
if user.get("mode") == "supabase":
    from pfa.data.supabase_store import load_holdings
    holdings = load_holdings(user["user_id"])
else:
    from agents.secretary_agent import load_portfolio
    holdings = load_portfolio().get("holdings", [])

# --- Empty state: onboarding ---
if not holdings:
    st.markdown("""
<div class="empty-state">
    <div class="icon">📊</div>
    <div class="title">Welcome to PFA</div>
    <div class="desc">Add your first holding to get started</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="onboard-card"><div class="icon">🔍</div><div class="title">智能搜索</div><div class="desc">代码或名称快速添加</div></div>', unsafe_allow_html=True)
    c2.markdown('<div class="onboard-card"><div class="icon">📸</div><div class="title">截图识别</div><div class="desc">AI 自动提取持仓</div></div>', unsafe_allow_html=True)
    c3.markdown('<div class="onboard-card"><div class="icon">📄</div><div class="title">文件导入</div><div class="desc">CSV / JSON 批量导入</div></div>', unsafe_allow_html=True)

    st.markdown("### 搜索添加")
    from pfa.stock_search import search_stock
    q = st.text_input("搜索股票", placeholder="茅台、00700、AAPL")
    if q and len(q.strip()) >= 1:
        results = search_stock(q)
        if results:
            for r in results[:5]:
                ca, cb = st.columns([4, 1])
                ca.markdown(f"**{r['code']}** {r['name']} · {r['market_raw']}")
                if cb.button("添加", key=f"add_{r['code']}"):
                    new_h = {"symbol": r["code"], "name": r["name"], "market": r["market"], "source": "search"}
                    if user.get("mode") == "supabase":
                        from pfa.data.supabase_store import save_holdings
                        save_holdings(user["user_id"], [new_h])
                    else:
                        from agents.secretary_agent import add_holding
                        add_holding(r["code"], r["name"], r["market"], 0, 0, 0, "search")
                    st.rerun()
    st.stop()

# --- Has holdings: Portfolio Hub ---
from html import escape
from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
from app.ai_expert import render_expert_chat, inject_morning_greeting
from app.notifications import add_notification

# Fetch data
fx = get_fx_rates()
prices = get_realtime_prices(holdings)
val = calculate_portfolio_value(holdings, prices, fx)

total_v = val["total_value_cny"]
total_pnl = val["total_pnl_cny"]
total_pct = val["total_pnl_pct"]
pnl_color = COLORS["up"] if total_pnl >= 0 else COLORS["down"]
sign = "+" if total_pnl >= 0 else ""

# Morning greeting
inject_morning_greeting(val)

# --- Metrics row ---
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><div class="label">Total Portfolio</div><div class="value">¥{total_v:,.0f}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><div class="label">Total Return</div><div class="value" style="color:{pnl_color};">{sign}¥{total_pnl:,.0f}</div><div class="change" style="color:{pnl_color};">{sign}{total_pct:.2f}%</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><div class="label">Holdings</div><div class="value">{val["holding_count"]}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><div class="label">Accounts</div><div class="value">{val["account_count"]}</div></div>', unsafe_allow_html=True)

# --- Main layout: Holdings + AI Chat ---
st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
col_left, col_right = st.columns([3, 2])

# --- LEFT: Holdings Table ---
with col_left:
    st.markdown('<h3 style="margin-bottom:12px;">HOLDINGS</h3>', unsafe_allow_html=True)

    tbl = '<table class="fin-table"><thead><tr>'
    for col_name in ["Symbol", "Name", "Price", "Cost", "Qty", "Value", "Return", "%"]:
        align = ' class="r"' if col_name not in ["Symbol", "Name"] else ""
        tbl += f"<th{align}>{col_name}</th>"
    tbl += "</tr></thead><tbody>"

    for acct_name, acct_data in val["by_account"].items():
        tbl += f'<tr class="group-row"><td colspan="8">{escape(acct_name)} · ¥{acct_data["value"]:,.0f}</td></tr>'

        for h in acct_data["holdings"]:
            pnl = h["pnl_cny"]
            pct = h["pnl_pct"]
            cls = "up" if pnl >= 0 else "down"
            ps = "+" if pnl >= 0 else ""

            tbl += "<tr>"
            tbl += f'<td><a class="sym" href="/?page=ticker&symbol={h["symbol"]}">{h["symbol"]}</a></td>'
            tbl += f'<td>{escape(h.get("name",""))}</td>'
            tbl += f'<td class="r">{h.get("current_price","—")}</td>'
            tbl += f'<td class="r muted">{h.get("cost_price","—")}</td>'
            tbl += f'<td class="r">{h.get("quantity","—")}</td>'
            tbl += f'<td class="r">¥{h["value_cny"]:,.0f}</td>'
            tbl += f'<td class="r {cls}">{ps}{pnl:,.0f}</td>'
            tbl += f'<td class="r {cls}">{ps}{pct:.1f}%</td>'
            tbl += "</tr>"

    tbl += "</tbody></table>"
    st.markdown(tbl, unsafe_allow_html=True)

# --- RIGHT: AI Expert Chat ---
with col_right:
    render_expert_chat(holdings, val, user)
