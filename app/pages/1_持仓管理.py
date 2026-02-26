"""持仓大盘 (Portfolio Command Center) — 总资产 + 多账户 + AI 录入"""

import json, sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from app.theme import inject_theme, theme_toggle, COLORS
from agents.secretary_agent import (
    load_portfolio, save_portfolio, validate_portfolio,
    add_holding, update_holdings_bulk,
    parse_csv_holdings, parse_json_holdings,
)
from pfa.stock_search import search_stock
from pfa.screenshot_ocr import extract_holdings_from_image
from pfa.ai_portfolio_assistant import parse_portfolio_command

inject_theme()
theme_toggle()

CST = timezone(timedelta(hours=8))
dark = st.session_state.get("dark_mode", True)
portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

# ===================================================================
# Global Net Worth Banner
# ===================================================================
st.header("持仓大盘")

if holdings:
    # Calculate portfolio value
    try:
        from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
        with st.spinner("获取实时行情..."):
            fx = get_fx_rates()
            prices = get_realtime_prices(holdings)
            val = calculate_portfolio_value(holdings, prices, fx)

        # Top metrics row
        c1, c2, c3, c4 = st.columns(4)

        total_v = val["total_value_cny"]
        total_pnl = val["total_pnl_cny"]
        total_pct = val["total_pnl_pct"]
        pnl_color = COLORS["positive"] if total_pnl >= 0 else COLORS["negative"]

        with c1:
            st.markdown(f"""<div class="pfa-card">
<div style="font-size:12px; color:{'#999' if dark else '#666'};">总资产 (CNY)</div>
<div style="font-size:28px; font-weight:800;">¥{total_v:,.0f}</div>
</div>""", unsafe_allow_html=True)

        with c2:
            sign = "+" if total_pnl >= 0 else ""
            st.markdown(f"""<div class="pfa-card" style="border-left:4px solid {pnl_color};">
<div style="font-size:12px; color:{'#999' if dark else '#666'};">总盈亏</div>
<div style="font-size:24px; font-weight:700; color:{pnl_color};">{sign}¥{total_pnl:,.0f}</div>
<div style="font-size:14px; color:{pnl_color};">{sign}{total_pct:.2f}%</div>
</div>""", unsafe_allow_html=True)

        with c3:
            st.markdown(f"""<div class="pfa-card">
<div style="font-size:12px; color:{'#999' if dark else '#666'};">标的 / 账户</div>
<div style="font-size:24px; font-weight:700;">{val['holding_count']} / {val['account_count']}</div>
</div>""", unsafe_allow_html=True)

        with c4:
            mkt_text = " · ".join(f"{k}:{v['count']}" for k, v in val["by_market"].items())
            fx_text = " · ".join(f"{k}:{v:.2f}" for k, v in fx.items() if k != "CNY")
            st.markdown(f"""<div class="pfa-card">
<div style="font-size:12px; color:{'#999' if dark else '#666'};">市场分布</div>
<div style="font-size:16px; font-weight:600;">{mkt_text}</div>
<div style="font-size:11px; color:{'#666' if dark else '#999'};">汇率: {fx_text}</div>
</div>""", unsafe_allow_html=True)

        # ===================================================================
        # Holdings by Account
        # ===================================================================
        st.markdown("---")
        st.subheader("按账户查看")

        for acct_name, acct_data in val["by_account"].items():
            acct_pnl = acct_data["pnl"]
            pnl_sign = "+" if acct_pnl >= 0 else ""
            acct_color = COLORS["positive"] if acct_pnl >= 0 else COLORS["negative"]

            with st.expander(
                f"**{acct_name}** · ¥{acct_data['value']:,.0f} · "
                f"{pnl_sign}¥{acct_pnl:,.0f} · {len(acct_data['holdings'])} 标的",
                expanded=True,
            ):
                rows = []
                for h in acct_data["holdings"]:
                    pnl_str = f"{'+' if h['pnl_cny']>=0 else ''}{h['pnl_cny']:,.0f}"
                    pct_str = f"{'+' if h['pnl_pct']>=0 else ''}{h['pnl_pct']:.1f}%"
                    rows.append({
                        "代码": h["symbol"],
                        "名称": h.get("name", ""),
                        "市场": h.get("market", ""),
                        "现价": h.get("current_price", ""),
                        "成本": h.get("cost_price", ""),
                        "数量": h.get("quantity", ""),
                        "市值(CNY)": f"¥{h['value_cny']:,.0f}",
                        "盈亏": pnl_str,
                        "涨跌%": pct_str,
                    })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except Exception as e:
        st.warning(f"实时估值暂不可用: {e}")
        # Fallback: simple table
        df = pd.DataFrame(holdings)
        cols = [c for c in ["symbol", "name", "market", "cost_price", "quantity", "account"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
else:
    st.info("暂无持仓。使用下方 AI 助理或其他方式添加。")

# ===================================================================
# AI Portfolio Assistant
# ===================================================================
st.markdown("---")
st.subheader("AI 记账助理")
st.caption("自然语言录入，例如：「平安证券加仓 500 股中海油，价格 21.5」")

ai_input = st.chat_input("输入持仓操作指令...")

if ai_input:
    with st.chat_message("user"):
        st.markdown(ai_input)

    with st.chat_message("assistant"):
        with st.spinner("解析中..."):
            result = parse_portfolio_command(ai_input)

        if "error" in result:
            st.error(f"解析失败: {result['error']}")
        else:
            action = result.get("action", "?")
            sym = result.get("symbol", "?")
            name = result.get("name", "?")
            qty = result.get("quantity", 0)
            price = result.get("price", 0)
            acct = result.get("account", "")
            conf = result.get("confidence", 0)

            action_text = {"add": "买入/加仓", "remove": "卖出/减仓", "update": "更新"}.get(action, action)

            st.markdown(f"""
**解析结果** (置信度: {conf}%)

| 项目 | 值 |
|---|---|
| 操作 | {action_text} |
| 代码 | {sym} |
| 名称 | {name} |
| 市场 | {result.get('market', '?')} |
| 数量 | {qty} |
| 价格 | {price} |
| 账户 | {acct or '默认'} |
""")

            if st.button("确认执行", type="primary", key="ai_confirm"):
                if action == "add":
                    add_holding(sym, name, result.get("market", "A"),
                                price, qty, 0, "ai_assistant")
                    if acct:
                        p = load_portfolio()
                        for h in p["holdings"]:
                            if h["symbol"] == sym and not h.get("account"):
                                h["account"] = acct
                        save_portfolio(p)
                    st.success(f"已添加 {name}({sym}) {qty}股 @{price}")
                    st.rerun()
                elif action == "remove":
                    st.info(f"减仓功能开发中。请在表格编辑中手动修改数量。")

# ===================================================================
# Quick Actions: Search / Upload / CSV
# ===================================================================
st.markdown("---")
tab_search, tab_screenshot, tab_upload = st.tabs(["智能搜索", "截图识别", "文件导入"])

with tab_search:
    query = st.text_input("搜索股票", placeholder="代码或名称，如：茅台、00700、AAPL",
                          key="stock_search")
    if query and len(query.strip()) >= 1:
        results = search_stock(query)
        if results:
            options = {f"{r['code']}  {r['name']}  ({r['market_raw']})": r for r in results}
            sel = st.radio("选择", list(options.keys()), key="search_sel")
            s = options[sel]
            with st.form("search_add", clear_on_submit=False):
                c1, c2, c3 = st.columns(3)
                cost = c1.number_input("成本价", min_value=0.0, step=0.01, format="%.2f")
                qty = c2.number_input("数量", min_value=0, step=100)
                acct = c3.text_input("账户", value="默认")
                if st.form_submit_button("添加", type="primary"):
                    add_holding(s["code"], s["name"], s["market"], cost, int(qty), 0, "search")
                    if acct.strip() and acct.strip() != "默认":
                        p = load_portfolio()
                        for h in p["holdings"]:
                            if h["symbol"] == s["code"] and not h.get("account"):
                                h["account"] = acct.strip()
                        save_portfolio(p)
                    st.success(f"已添加 {s['name']}")
                    st.rerun()

with tab_screenshot:
    st.caption("上传券商截图，AI 自动提取持仓")
    img = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "webp"], key="ocr_img")
    ocr_acct = st.text_input("账户名称", placeholder="如：平安证券", key="ocr_acct")
    if img:
        st.image(img, use_container_width=True)
        if st.button("AI 识别", type="primary", key="ocr_go"):
            with st.spinner("识别中..."):
                r = extract_holdings_from_image(img.read(),
                    f"image/{img.type.split('/')[-1]}" if img.type else "image/png")
            if r["status"] == "ok" and r["holdings"]:
                st.session_state["ocr_data"] = r["holdings"]
                st.success(f"识别到 {len(r['holdings'])} 条")
            else:
                st.error(r.get("error", "识别失败"))

    ocr = st.session_state.get("ocr_data")
    if ocr:
        edited = st.data_editor(pd.DataFrame(ocr), num_rows="dynamic",
                                use_container_width=True, hide_index=True)
        if st.button("导入持仓", type="primary", key="ocr_import"):
            now = datetime.now(CST).isoformat()
            p = load_portfolio()
            for _, row in edited.iterrows():
                sym = str(row.get("symbol", "")).strip()
                if not sym:
                    continue
                entry = {"symbol": sym, "name": str(row.get("name", "")),
                         "market": row.get("market", "A"), "source": "ocr",
                         "updated_at": now}
                for k in ("cost_price", "quantity"):
                    v = row.get(k)
                    if v and float(v) > 0:
                        entry[k] = float(v)
                if ocr_acct.strip():
                    entry["account"] = ocr_acct.strip()
                p.setdefault("holdings", []).append(entry)
            save_portfolio(p)
            del st.session_state["ocr_data"]
            st.success("已导入")
            st.rerun()

with tab_upload:
    st.caption("CSV 或 JSON 批量导入")
    uploaded = st.file_uploader("上传文件", type=["csv", "json"], key="file_up")
    if uploaded:
        raw = uploaded.read().decode("utf-8")
        try:
            parsed = (parse_csv_holdings(raw) if uploaded.name.endswith(".csv")
                      else parse_json_holdings(raw))
            if parsed:
                st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)
                if st.button("导入", type="primary", key="file_go"):
                    p = load_portfolio()
                    p.get("holdings", []).extend(parsed)
                    update_holdings_bulk(p["holdings"])
                    st.success(f"已导入 {len(parsed)} 条")
                    st.rerun()
        except Exception as e:
            st.error(str(e))
