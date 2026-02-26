"""持仓大盘 — 左侧持仓 + 右侧 Ask PFA 对话 (NBOT 风格)"""

import json, sys, urllib.parse
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from app.theme import inject_theme, theme_toggle, COLORS
from app.page_utils import page_init
from agents.secretary_agent import (
    load_portfolio, save_portfolio, add_holding, update_holdings_bulk,
    parse_csv_holdings, parse_json_holdings,
)
from pfa.stock_search import search_stock
from pfa.screenshot_ocr import extract_holdings_from_image
from pfa.ai_portfolio_assistant import parse_portfolio_command


user = page_init()

CST = timezone(timedelta(hours=8))
dark = st.session_state.get("dark_mode", True)
portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])
card_bg = COLORS["bg_card_dark"] if dark else COLORS["bg_card_light"]
border = COLORS["border_dark"] if dark else COLORS["border_light"]
text_c = COLORS["text_dark"] if dark else COLORS["text_light"]
sub_c = "#999" if dark else "#666"

st.header("持仓大盘")

# ===================================================================
# Top metrics row
# ===================================================================
if holdings:
    try:
        from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
        fx = get_fx_rates()
        prices = get_realtime_prices(holdings)
        val = calculate_portfolio_value(holdings, prices, fx)

        total_v = val["total_value_cny"]
        total_pnl = val["total_pnl_cny"]
        total_pct = val["total_pnl_pct"]
        pnl_color = COLORS["positive"] if total_pnl >= 0 else COLORS["negative"]
        sign = "+" if total_pnl >= 0 else ""

        mc = st.columns(4)
        mc[0].markdown(f'<div class="pfa-card"><div style="font-size:11px;color:{sub_c};">总资产 CNY</div><div style="font-size:26px;font-weight:800;">¥{total_v:,.0f}</div></div>', unsafe_allow_html=True)
        mc[1].markdown(f'<div class="pfa-card" style="border-left:4px solid {pnl_color};"><div style="font-size:11px;color:{sub_c};">总盈亏</div><div style="font-size:22px;font-weight:700;color:{pnl_color};">{sign}¥{total_pnl:,.0f}</div><div style="font-size:13px;color:{pnl_color};">{sign}{total_pct:.2f}%</div></div>', unsafe_allow_html=True)
        mc[2].markdown(f'<div class="pfa-card"><div style="font-size:11px;color:{sub_c};">标的 / 账户</div><div style="font-size:22px;font-weight:700;">{val["holding_count"]} / {val["account_count"]}</div></div>', unsafe_allow_html=True)
        mkt_t = " · ".join(f"{k}:{v['count']}" for k, v in val["by_market"].items())
        mc[3].markdown(f'<div class="pfa-card"><div style="font-size:11px;color:{sub_c};">市场分布</div><div style="font-size:15px;font-weight:600;">{mkt_t}</div></div>', unsafe_allow_html=True)
    except Exception as e:
        val = None
        st.warning(f"行情暂不可用: {e}")

# ===================================================================
# Main layout: Left = Holdings | Right = Ask PFA
# ===================================================================
col_left, col_right = st.columns([7, 3])

# --- LEFT: Holdings by account ---
with col_left:
    st.markdown("### 持仓明细")

    if holdings and val:
        for acct_name, acct_data in val["by_account"].items():
            apnl = acct_data["pnl"]
            ac = COLORS["positive"] if apnl >= 0 else COLORS["negative"]
            ps = "+" if apnl >= 0 else ""

            with st.expander(f"**{acct_name}** · ¥{acct_data['value']:,.0f} · {ps}¥{apnl:,.0f}", expanded=True):
                html = f'<table style="width:100%;border-collapse:collapse;font-size:13px;table-layout:auto;">'
                html += f'<tr style="border-bottom:1px solid {border};">'
                for col in ["代码", "名称", "现价", "成本", "数量", "盈亏", "涨跌%"]:
                    html += f'<th style="text-align:right;padding:8px 10px;color:{sub_c};font-weight:600;font-size:12px;white-space:nowrap;">{col}</th>'
                html += '</tr>'

                for h in acct_data["holdings"]:
                    pnl = h["pnl_cny"]
                    pct = h["pnl_pct"]
                    pc = COLORS["positive"] if pnl >= 0 else COLORS["negative"]
                    ps2 = "+" if pnl >= 0 else ""
                    td = f'padding:8px 10px;white-space:nowrap;'
                    html += f'<tr style="border-bottom:1px solid {border};">'
                    ticker_link = f'/{urllib.parse.quote("个股深度")}?symbol={h["symbol"]}'
                    html += f'<td style="{td}"><a href="{ticker_link}" target="_self" style="color:{COLORS["accent"] if dark else COLORS["bullish"]};font-weight:600;text-decoration:none;">{h["symbol"]}</a></td>'
                    html += f'<td style="{td}color:{text_c};">{escape(h.get("name",""))}</td>'
                    html += f'<td style="{td}text-align:right;color:{text_c};">{h.get("current_price","—")}</td>'
                    html += f'<td style="{td}text-align:right;color:{sub_c};">{h.get("cost_price","—")}</td>'
                    html += f'<td style="{td}text-align:right;color:{text_c};">{h.get("quantity","—")}</td>'
                    html += f'<td style="{td}text-align:right;color:{pc};font-weight:600;">{ps2}{pnl:,.0f}</td>'
                    html += f'<td style="{td}text-align:right;color:{pc};">{ps2}{pct:.1f}%</td>'
                    html += '</tr>'
                html += '</table>'
                st.markdown(html, unsafe_allow_html=True)
    elif holdings:
        for h in holdings:
            st.text(f"{h['symbol']} {h.get('name','')} {h.get('quantity','')}")
    else:
        st.info("暂无持仓。使用右侧 AI 助理添加。")

    # ---------------------------------------------------------------
    # Memo Timeline
    # ---------------------------------------------------------------
    from agents.secretary_agent import get_all_memos
    all_memos = get_all_memos()
    if all_memos:
        st.markdown("---")
        st.markdown("### 投资备忘录")
        st.markdown(
            f'<div style="font-size:12px;color:{sub_c};margin-bottom:12px;">'
            '🔴 买入 &nbsp; 🟢 卖出 &nbsp; ⚪ 持有 &nbsp; 👁 观望 &nbsp; 📝 笔记'
            '</div>', unsafe_allow_html=True,
        )
        action_icons = {"buy": "🔴", "sell": "🟢", "hold": "⚪", "watch": "👁", "note": "📝"}
        for m in all_memos[:10]:
            icon = action_icons.get(m.get("action", "note"), "📝")
            t = m.get("time", "")[:16]
            sym = m.get("symbol", "")
            name = m.get("name", sym)
            text = escape(m.get("text", ""))
            qty_c = m.get("quantity_change", 0)
            price = m.get("price", 0)
            detail = ""
            if qty_c:
                detail += f" · {'+'if qty_c>0 else ''}{qty_c:.0f}股"
            if price:
                detail += f" @{price}"

            st.markdown(f"""<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid {border};">
<div style="font-size:20px;padding-top:2px;">{icon}</div>
<div style="flex:1;">
<div style="font-size:13px;font-weight:600;color:{text_c};">{escape(name)} <span style="color:{sub_c};font-weight:400;">{sym}{detail}</span></div>
<div style="font-size:13px;color:{text_c};margin-top:2px;">{text}</div>
<div style="font-size:11px;color:{sub_c};margin-top:4px;">{t}</div>
</div>
</div>""", unsafe_allow_html=True)

    # Quick add tabs
    st.markdown("---")
    tab_s, tab_ocr, tab_f = st.tabs(["智能搜索", "截图识别", "文件导入"])

    with tab_s:
        q = st.text_input("搜索股票", placeholder="茅台、00700、AAPL", key="ss")
        if q and len(q.strip()) >= 1:
            results = search_stock(q)
            if results:
                opts = {f"{r['code']}  {r['name']}  ({r['market_raw']})": r for r in results}
                sel = st.radio("选择", list(opts.keys()), key="ssel")
                s = opts[sel]
                with st.form("sadd"):
                    c1, c2, c3 = st.columns(3)
                    cost = c1.number_input("成本价", min_value=0.0, step=0.01, format="%.2f")
                    qty = c2.number_input("数量", min_value=0, step=100)
                    acct = c3.text_input("账户", value="默认")
                    if st.form_submit_button("添加", type="primary"):
                        add_holding(s["code"], s["name"], s["market"], cost, int(qty), 0, "search")
                        if acct.strip() != "默认":
                            p = load_portfolio()
                            for hh in p["holdings"]:
                                if hh["symbol"] == s["code"] and not hh.get("account"):
                                    hh["account"] = acct.strip()
                            save_portfolio(p)
                        st.rerun()

    with tab_ocr:
        img = st.file_uploader("上传截图", type=["png","jpg","jpeg","webp"], key="oi")
        oa = st.text_input("账户", placeholder="平安证券", key="oa")
        if img:
            st.image(img, use_container_width=True)
            if st.button("AI 识别", type="primary", key="og"):
                with st.spinner("识别中..."):
                    r = extract_holdings_from_image(img.read(), "image/png")
                if r["status"] == "ok" and r["holdings"]:
                    st.session_state["ocr_data"] = r["holdings"]
                    st.success(f"{len(r['holdings'])} 条")
                else:
                    st.error(r.get("error","失败"))
        ocr = st.session_state.get("ocr_data")
        if ocr:
            ed = st.data_editor(pd.DataFrame(ocr), num_rows="dynamic", use_container_width=True, hide_index=True)
            if st.button("导入", type="primary", key="oimp"):
                p = load_portfolio()
                now = datetime.now(CST).isoformat()
                for _, row in ed.iterrows():
                    sym = str(row.get("symbol","")).strip()
                    if not sym: continue
                    e = {"symbol":sym, "name":str(row.get("name","")), "market":row.get("market","A"), "source":"ocr", "updated_at":now}
                    for k in ("cost_price","quantity"):
                        v = row.get(k)
                        if v and float(v)>0: e[k]=float(v)
                    if oa.strip(): e["account"]=oa.strip()
                    p.setdefault("holdings",[]).append(e)
                save_portfolio(p)
                del st.session_state["ocr_data"]
                st.rerun()

    with tab_f:
        up = st.file_uploader("CSV / JSON", type=["csv","json"], key="fu")
        if up:
            raw = up.read().decode("utf-8")
            try:
                parsed = parse_csv_holdings(raw) if up.name.endswith(".csv") else parse_json_holdings(raw)
                if parsed:
                    st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)
                    if st.button("导入", type="primary", key="fimp"):
                        p = load_portfolio()
                        p.get("holdings",[]).extend(parsed)
                        update_holdings_bulk(p["holdings"])
                        st.rerun()
            except Exception as e:
                st.error(str(e))

# --- RIGHT: Ask PFA (NBOT style) ---
with col_right:
    st.markdown(f"""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
    <span style="font-size:20px;">✨</span>
    <span style="font-size:17px; font-weight:700; color:{text_c};">Ask PFA</span>
    <span style="background:{COLORS['accent']}; color:#000; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600;">Live</span>
</div>""", unsafe_allow_html=True)

    # Chat container
    if "portfolio_chat" not in st.session_state:
        st.session_state["portfolio_chat"] = [
            {"role": "assistant", "content": "你好！我是 PFA 记账助理。\n\n你可以对我说：\n- 「加仓 500 股中海油 价格 21.5」\n- 「腾讯控股数量改为 300」\n- 「删除上海机场」\n- 「记录：看好茅台渠道改革长期逻辑」"}
        ]

    # Render chat bubbles
    chat_container = st.container(height=450)
    with chat_container:
        for msg in st.session_state["portfolio_chat"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input
    ai_input = st.chat_input("管理持仓...")

    if ai_input:
        st.session_state["portfolio_chat"].append({"role": "user", "content": ai_input})

        with st.spinner("解析中..."):
            result = parse_portfolio_command(ai_input)

        if "error" in result:
            reply = f"❌ {result['error']}"
        else:
            action = result.get("action", "?")
            sym = result.get("symbol", "?")
            name = result.get("name", "?")
            qty = result.get("quantity", 0)
            price = result.get("price", 0)
            acct = result.get("account", "")
            market = result.get("market", "A")
            now_str = datetime.now(CST).isoformat()
            p = load_portfolio()

            if action == "add":
                entry = {"symbol": sym, "name": name, "market": market,
                         "source": "ai_assistant", "updated_at": now_str}
                if qty > 0: entry["quantity"] = qty
                if price > 0: entry["cost_price"] = price
                if acct: entry["account"] = acct
                p.setdefault("holdings", []).append(entry)
                save_portfolio(p)
                reply = f"✅ 已买入 **{name}**({sym}) {qty}股" + (f" @{price}" if price else "")

            elif action == "update":
                updated = False
                for h in p.get("holdings", []):
                    if h["symbol"] == sym:
                        if qty >= 0: h["quantity"] = qty
                        if price > 0: h["cost_price"] = price
                        h["updated_at"] = now_str
                        updated = True
                        break
                if updated:
                    save_portfolio(p)
                    reply = f"✅ 已更新 **{name}**({sym}) → 数量 {qty}" + (f" 价格 {price}" if price else "")
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
                memo_text = result.get("text", ai_input)
                memo_action = result.get("memo_action", "note")
                ok = add_memo(sym, memo_action, memo_text, qty, price)
                if ok:
                    icon = {"buy":"🔴","sell":"🟢","hold":"⚪","watch":"👁","note":"📝"}.get(memo_action,"📝")
                    reply = f"{icon} 已记录 **{name}**({sym}) 备忘：{memo_text[:50]}"
                else:
                    reply = f"⚠️ 未找到 {name}({sym})，请先添加持仓"

            else:
                reply = f"❓ 未知操作: {action}"

        st.session_state["portfolio_chat"].append({"role": "assistant", "content": reply})
        st.rerun()
