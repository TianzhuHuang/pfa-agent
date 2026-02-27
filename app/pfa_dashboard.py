"""
PFA v2 — Portfolio Hub (基金经理级)

Exception-Driven: 今日异常 → 持仓概览 → AI 助理
"""

import sys, json, os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from html import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="PFA", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user, render_login_page

inject_v2_theme()

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

# --- Auth ---
user = get_user()
if not user.get("user_id"):
    render_login_page()
    st.stop()

render_topnav(active="portfolio", user_email=user.get("email", ""))

# --- Load holdings ---
holdings = []
if user.get("mode") == "supabase":
    from pfa.data.supabase_store import load_holdings
    holdings = load_holdings(user["user_id"])
else:
    from agents.secretary_agent import load_portfolio
    holdings = load_portfolio().get("holdings", [])

# ===================================================================
# ONBOARDING (empty state)
# ===================================================================
if not holdings:
    st.markdown("""
<style>
@keyframes fadeInUp { from{opacity:0;transform:translateY(30px)} to{opacity:1;transform:translateY(0)} }
@keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }
.onboard-hero{text-align:center;padding:60px 20px 40px;animation:fadeInUp .8s ease-out}
.onboard-hero .icon{font-size:56px;margin-bottom:16px;animation:pulse 2s infinite}
.onboard-hero .title{font-size:28px;font-weight:700;color:#E8EAED;margin-bottom:8px}
.onboard-hero .desc{font-size:15px;color:#9AA0A6;max-width:400px;margin:0 auto}
.onboard-steps{display:flex;justify-content:center;gap:12px;margin:24px 0;animation:fadeInUp 1s ease-out .3s both}
.onboard-step{display:flex;align-items:center;gap:8px;font-size:13px;color:#5F6368}
.onboard-step .num{width:24px;height:24px;border-radius:50%;background:#4285F4;color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}
</style>
<div class="onboard-hero">
    <div class="icon">📊</div>
    <div class="title">Welcome to PFA</div>
    <div class="desc">添加你的第一笔持仓，开始智能投研之旅</div>
</div>
<div class="onboard-steps">
    <div class="onboard-step"><span class="num">1</span> 录入持仓</div>
    <div class="onboard-step" style="color:#2D3139;">→</div>
    <div class="onboard-step"><span class="num" style="background:#5F6368;">2</span> AI 分析</div>
    <div class="onboard-step" style="color:#2D3139;">→</div>
    <div class="onboard-step"><span class="num" style="background:#5F6368;">3</span> 每日推送</div>
</div>""", unsafe_allow_html=True)

    from pfa.stock_search import search_stock
    from pfa.screenshot_ocr import extract_holdings_from_image
    from agents.secretary_agent import parse_csv_holdings, parse_json_holdings
    import pandas as pd

    def _save(new_list):
        if user.get("mode") == "supabase":
            from pfa.data.supabase_store import load_holdings as lh, save_holdings as sh
            sh(user["user_id"], lh(user["user_id"]) + new_list)
        else:
            from agents.secretary_agent import add_holding
            for h in new_list:
                add_holding(h.get("symbol",""), h.get("name",""), h.get("market","A"), h.get("cost_price",0), h.get("quantity",0), 0, h.get("source","manual"))

    tab_s, tab_o, tab_f = st.tabs(["🔍 智能搜索", "📸 截图识别", "📄 文件导入"])
    with tab_s:
        q = st.text_input("搜索股票", placeholder="茅台、00700、AAPL")
        if q and len(q.strip()) >= 1:
            for r in (search_stock(q) or [])[:6]:
                ca, cb = st.columns([4, 1])
                ca.markdown(f"**{r['code']}** {r['name']} · {r['market_raw']}")
                if cb.button("添加", key=f"a_{r['code']}", type="primary"):
                    _save([{"symbol": r["code"], "name": r["name"], "market": r["market"], "source": "search"}])
                    st.rerun()
    with tab_o:
        st.caption("上传券商截图，AI 自动识别")
        img = st.file_uploader("上传", type=["png","jpg","jpeg","webp"], key="oi")
        if img:
            ib = img.getvalue()
            st.image(ib, width=300)
            if st.button("🤖 AI 识别", type="primary", use_container_width=True, key="ob"):
                with st.spinner("识别中..."):
                    r = extract_holdings_from_image(ib, img.type or "image/png")
                if r["status"] == "ok" and r["holdings"]:
                    st.session_state["oo"] = r["holdings"]
                    st.success(f"识别到 {len(r['holdings'])} 条")
                else:
                    st.error(r.get("error","失败"))
        oo = st.session_state.get("oo")
        if oo:
            ed = st.data_editor(pd.DataFrame(oo), num_rows="dynamic", use_container_width=True, hide_index=True)
            ca, cb = st.columns(2)
            if ca.button("✅ 确认导入", type="primary", use_container_width=True, key="oci"):
                _save([{**dict(r), "source":"ocr"} for _,r in ed.iterrows() if str(r.get("symbol","")).strip()])
                del st.session_state["oo"]
                st.rerun()
            if cb.button("❌ 清除", use_container_width=True, key="occ"):
                del st.session_state["oo"]
                st.rerun()
    with tab_f:
        up = st.file_uploader("CSV/JSON", type=["csv","json"], key="fu")
        if up:
            raw = up.read().decode("utf-8")
            try:
                parsed = parse_csv_holdings(raw) if up.name.endswith(".csv") else parse_json_holdings(raw)
                if parsed:
                    st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)
                    if st.button("导入", type="primary", key="fi"):
                        _save(parsed)
                        st.rerun()
            except Exception as e:
                st.error(str(e))
    st.stop()

# ===================================================================
# PORTFOLIO HUB (has holdings)
# ===================================================================
from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
from app.ai_expert import render_expert_chat, inject_morning_greeting
from app.charts import render_allocation_pie, render_market_distribution, render_pnl_waterfall

fx = get_fx_rates()
prices = get_realtime_prices(holdings)
val = calculate_portfolio_value(holdings, prices, fx)

total_v = val["total_value_cny"]
total_pnl = val["total_pnl_cny"]
total_pct = val["total_pnl_pct"]
pnl_c = COLORS["up"] if total_pnl >= 0 else COLORS["down"]
sign = "+" if total_pnl >= 0 else ""

# Calculate today's P&L for each holding
all_holdings_flat = []
for acct_data in val["by_account"].values():
    for h in acct_data["holdings"]:
        p = prices.get(h["symbol"], {})
        chg = p.get("change", 0)
        qty = float(h.get("quantity", 0) or 0)
        h["today_pnl"] = chg * qty
        h["today_chg_pct"] = p.get("percent", 0)
        h["weight_pct"] = (h["value_cny"] / total_v * 100) if total_v > 0 else 0
        h["update_time"] = p.get("update_time", "")
        all_holdings_flat.append(h)

total_today_pnl = sum(h.get("today_pnl", 0) for h in all_holdings_flat)

inject_morning_greeting(val)

# --- Exception Banner (Top1) ---
exceptions = []
for h in all_holdings_flat:
    pct = abs(h.get("today_chg_pct", 0))
    if pct >= 3:
        icon = "🔴" if h["today_chg_pct"] < 0 else "📈"
        exceptions.append(f'{icon} {h.get("name","")[:4]} {h["today_chg_pct"]:+.1f}%')

if exceptions:
    st.markdown(f"""
<div style="background:#1A1D26;border:1px solid #2D3139;border-radius:8px;padding:10px 16px;margin-bottom:16px;display:flex;gap:16px;flex-wrap:wrap;font-size:13px;">
    <span style="color:#5F6368;font-weight:600;">⚡ 今日异常</span>
    {''.join(f'<span style="color:#E8EAED;">{e}</span>' for e in exceptions[:5])}
</div>""", unsafe_allow_html=True)

# --- Metrics (Top4: Chinese terms) ---
update_time = ""
for h in all_holdings_flat:
    t = h.get("update_time", "")
    if t and len(t) > len(update_time):
        update_time = t

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><div class="label">总资产</div><div class="value">¥{total_v:,.0f}</div></div>', unsafe_allow_html=True)

today_c = COLORS["up"] if total_today_pnl >= 0 else COLORS["down"]
ts = "+" if total_today_pnl >= 0 else ""
c2.markdown(f'<div class="metric-card"><div class="label">今日盈亏</div><div class="value" style="color:{today_c};">{ts}¥{total_today_pnl:,.0f}</div></div>', unsafe_allow_html=True)

c3.markdown(f'<div class="metric-card"><div class="label">累计盈亏</div><div class="value" style="color:{pnl_c};">{sign}¥{total_pnl:,.0f}</div><div class="change" style="color:{pnl_c};">{sign}{total_pct:.2f}%</div></div>', unsafe_allow_html=True)

c4.markdown(f'<div class="metric-card"><div class="label">{val["holding_count"]} 只标的 · {val["account_count"]} 个账户</div><div class="value" style="font-size:14px;color:#5F6368;">更新: {update_time[-8:] if update_time else "—"}</div></div>', unsafe_allow_html=True)

# --- Main: Table + Charts + AI ---
st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
col_main, col_side = st.columns([5, 3])

with col_main:
    # Holdings table (Top6: +4 columns)
    st.markdown('<h3 style="margin-bottom:12px;">持仓明细</h3>', unsafe_allow_html=True)

    tbl = '<table class="fin-table"><thead><tr>'
    for c in ["代码", "名称", "现价", "今日", "成本", "数量", "市值", "仓位", "累计盈亏", "收益率"]:
        align = ' class="r"' if c not in ["代码", "名称"] else ""
        tbl += f"<th{align}>{c}</th>"
    tbl += "</tr></thead><tbody>"

    for acct_name, acct_data in val["by_account"].items():
        tbl += f'<tr class="group-row"><td colspan="10">{escape(acct_name)} · ¥{acct_data["value"]:,.0f}</td></tr>'

        for h in acct_data["holdings"]:
            pnl = h["pnl_cny"]
            pct = h["pnl_pct"]
            cls = "up" if pnl >= 0 else "down"
            ps = "+" if pnl >= 0 else ""
            tp = h.get("today_pnl", 0)
            tc = "up" if tp >= 0 else "down"
            tps = "+" if tp >= 0 else ""
            w = h.get("weight_pct", 0)
            # Weight warning if > 30%
            w_style = f'color:{COLORS["up"]};font-weight:700;' if w > 30 else ""

            tbl += "<tr>"
            tbl += f'<td><a class="sym" href="/?page=ticker&symbol={h["symbol"]}">{h["symbol"]}</a></td>'
            tbl += f'<td>{escape(h.get("name","")[:6])}</td>'
            tbl += f'<td class="r">{h.get("current_price","—")}</td>'
            tbl += f'<td class="r {tc}">{tps}{tp:,.0f}</td>'
            tbl += f'<td class="r muted">{h.get("cost_price","—")}</td>'
            tbl += f'<td class="r">{h.get("quantity","—")}</td>'
            tbl += f'<td class="r">¥{h["value_cny"]:,.0f}</td>'
            tbl += f'<td class="r" style="{w_style}">{w:.1f}%</td>'
            tbl += f'<td class="r {cls}">{ps}{pnl:,.0f}</td>'
            tbl += f'<td class="r {cls}">{ps}{pct:.1f}%</td>'
            tbl += "</tr>"

    tbl += "</tbody></table>"
    st.markdown(tbl, unsafe_allow_html=True)

    # Charts row
    st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown('<h3>仓位分布</h3>', unsafe_allow_html=True)
        render_allocation_pie(all_holdings_flat, total_v)
    with ch2:
        st.markdown('<h3>今日盈亏贡献</h3>', unsafe_allow_html=True)
        render_pnl_waterfall(all_holdings_flat)

with col_side:
    render_expert_chat(holdings, val, user)
