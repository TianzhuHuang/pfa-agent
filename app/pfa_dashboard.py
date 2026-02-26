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
    <div class="desc">添加你的第一笔持仓，开始智能投研之旅</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    from pfa.stock_search import search_stock
    from pfa.screenshot_ocr import extract_holdings_from_image
    from agents.secretary_agent import parse_csv_holdings, parse_json_holdings
    import pandas as pd
    from datetime import datetime, timedelta, timezone as tz
    _CST = tz(timedelta(hours=8))

    def _save_new_holdings(new_list):
        if user.get("mode") == "supabase":
            from pfa.data.supabase_store import load_holdings, save_holdings
            existing = load_holdings(user["user_id"])
            existing.extend(new_list)
            save_holdings(user["user_id"], existing)
        else:
            from agents.secretary_agent import add_holding
            for h in new_list:
                add_holding(h.get("symbol",""), h.get("name",""), h.get("market","A"),
                            h.get("cost_price",0), h.get("quantity",0), 0, h.get("source","manual"))

    tab_search, tab_ocr, tab_csv = st.tabs(["🔍 智能搜索", "📸 截图识别", "📄 文件导入"])

    with tab_search:
        q = st.text_input("搜索股票代码或名称", placeholder="茅台、00700、AAPL、腾讯")
        if q and len(q.strip()) >= 1:
            results = search_stock(q)
            if results:
                for r in results[:6]:
                    ca, cb = st.columns([4, 1])
                    ca.markdown(f"**{r['code']}** {r['name']} · {r['market_raw']}")
                    if cb.button("添加", key=f"add_{r['code']}", type="primary"):
                        _save_new_holdings([{"symbol": r["code"], "name": r["name"], "market": r["market"], "source": "search"}])
                        st.rerun()
            else:
                st.caption("未找到匹配的股票")

    with tab_ocr:
        st.caption("上传券商持仓截图，AI 自动提取持仓数据")
        img = st.file_uploader("上传截图", type=["png","jpg","jpeg","webp"], key="onb_img")
        if img:
            # Read bytes first before displaying
            img_bytes = img.getvalue()
            # Show small preview
            st.image(img_bytes, width=300, caption="预览")
            mime = img.type or "image/png"

            if st.button("🤖 AI 识别持仓", type="primary", use_container_width=True, key="onb_ocr"):
                with st.spinner("通义千问 VL 识别中，请稍候..."):
                    r = extract_holdings_from_image(img_bytes, mime)
                if r["status"] == "ok" and r["holdings"]:
                    st.session_state["onb_ocr"] = r["holdings"]
                    st.success(f"✅ 识别到 {len(r['holdings'])} 条持仓")
                elif r.get("raw_response"):
                    st.warning("识别结果可能不完整")
                    st.text_area("模型输出", r["raw_response"], height=100)
                else:
                    st.error(f"识别失败: {r.get('error', '未知错误')}")

        ocr = st.session_state.get("onb_ocr")
        if ocr:
            st.markdown("---")
            st.markdown("**识别结果（可编辑）**")
            ed = st.data_editor(pd.DataFrame(ocr), num_rows="dynamic", use_container_width=True, hide_index=True)
            c_imp, c_clr = st.columns(2)
            if c_imp.button("✅ 确认导入", type="primary", use_container_width=True, key="onb_ocr_imp"):
                rows = [dict(row) for _, row in ed.iterrows() if str(row.get("symbol","")).strip()]
                for r in rows:
                    r["source"] = "ocr"
                _save_new_holdings(rows)
                del st.session_state["onb_ocr"]
                st.rerun()
            if c_clr.button("❌ 清除", use_container_width=True, key="onb_ocr_clr"):
                del st.session_state["onb_ocr"]
                st.rerun()

    with tab_csv:
        st.caption("上传 CSV 或 JSON 文件批量导入")
        up = st.file_uploader("上传文件", type=["csv","json"], key="onb_file")
        if up:
            raw = up.read().decode("utf-8")
            try:
                parsed = parse_csv_holdings(raw) if up.name.endswith(".csv") else parse_json_holdings(raw)
                if parsed:
                    st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)
                    if st.button("导入全部", type="primary", key="onb_file_imp"):
                        _save_new_holdings(parsed)
                        st.rerun()
            except Exception as e:
                st.error(str(e))

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
