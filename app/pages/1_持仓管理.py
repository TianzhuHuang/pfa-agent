"""持仓管理 — 智能搜索录入 / 截图识别 / 批量导入 / 多账户"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from app.theme import inject_theme, theme_toggle
inject_theme()
theme_toggle()
from agents.secretary_agent import (
    load_portfolio, save_portfolio, validate_portfolio,
    add_holding, remove_holding, update_holdings_bulk,
    parse_csv_holdings, parse_json_holdings,
)
from pfa.stock_search import search_stock
from pfa.screenshot_ocr import extract_holdings_from_image

MARKET_OPTIONS = ["A", "HK", "US", "OTHER"]
CST = timezone(timedelta(hours=8))

st.header("持仓管理")

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

# ===================================================================
# Current Holdings Display
# ===================================================================
st.subheader("当前持仓")
if holdings:
    df = pd.DataFrame(holdings)
    cols = [c for c in ["symbol", "name", "market", "cost_price",
                        "quantity", "position_pct", "source", "account"]
            if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

    accounts = set(h.get("account", "默认") for h in holdings)
    st.caption(f"共 {len(holdings)} 个标的 · {len(accounts)} 个账户")
else:
    st.info("暂无持仓。请通过下方方式添加。")

st.markdown("---")

# ===================================================================
# Tabs
# ===================================================================
tab_search, tab_screenshot, tab_upload, tab_edit = st.tabs(
    ["智能搜索添加", "截图识别", "文件导入", "表格编辑"]
)

# ===================================================================
# Tab 1: Smart Search Add
# ===================================================================
with tab_search:
    st.subheader("智能搜索添加")
    st.caption("输入代码、名称或拼音首字母，实时搜索 A 股 / 港股 / 美股")

    query = st.text_input("搜索股票", placeholder="输入代码或名称，如：茅台、00700、AAPL",
                          key="stock_search_input")

    if query and len(query.strip()) >= 1:
        results = search_stock(query)
        if results:
            options = {
                f"{r['code']}  {r['name']}  ({r['market_raw']})": r
                for r in results
            }
            selected_label = st.radio(
                "选择标的", list(options.keys()),
                key="search_select",
            )
            sel = options[selected_label]

            st.markdown(f"**已选择**: `{sel['code']}` {sel['name']} ({sel['market_raw']})")

            with st.form("add_from_search", clear_on_submit=False):
                c1, c2, c3 = st.columns(3)
                cost = c1.number_input("成本价", min_value=0.0, step=0.01, format="%.2f",
                                       key="search_cost")
                qty = c2.number_input("数量（股）", min_value=0, step=100,
                                      key="search_qty")
                account = c3.text_input("账户名称", value="默认", key="search_account")

                if st.form_submit_button("添加到持仓", type="primary"):
                    p = load_portfolio()
                    now = datetime.now(CST).isoformat()
                    h = {
                        "symbol": sel["code"], "name": sel["name"],
                        "market": sel["market"], "source": "search",
                        "updated_at": now,
                    }
                    if cost > 0:
                        h["cost_price"] = cost
                    if qty > 0:
                        h["quantity"] = int(qty)
                    if account.strip():
                        h["account"] = account.strip()
                    p.setdefault("holdings", []).append(h)
                    save_portfolio(p)
                    st.success(f"已添加 {sel['name']} ({sel['code']})")
                    st.rerun()
        else:
            st.caption("未找到匹配的股票")

# ===================================================================
# Tab 2: Screenshot OCR
# ===================================================================
with tab_screenshot:
    st.subheader("截图识别")
    st.caption("上传券商持仓截图，AI 自动提取持仓数据（使用通义千问 VL 多模态模型）")

    uploaded_img = st.file_uploader(
        "上传持仓截图", type=["png", "jpg", "jpeg", "webp"],
        key="screenshot_upload",
    )
    ocr_account = st.text_input("账户名称（可选）", value="", key="ocr_account",
                                placeholder="如：招商证券、富途")

    if uploaded_img:
        st.image(uploaded_img, caption="上传的截图", use_container_width=True)

        if st.button("AI 识别持仓", type="primary", key="ocr_btn"):
            with st.spinner("正在调用通义千问 VL 识别..."):
                img_bytes = uploaded_img.read()
                mime = f"image/{uploaded_img.type.split('/')[-1]}" if '/' in (uploaded_img.type or '') else "image/png"
                result = extract_holdings_from_image(img_bytes, mime)

            if result["status"] == "ok" and result["holdings"]:
                st.success(f"识别到 {len(result['holdings'])} 条持仓记录")
                st.session_state["ocr_holdings"] = result["holdings"]
            elif result["status"] == "partial":
                st.warning("识别结果可能不完整")
                st.text_area("模型原始输出", result.get("raw_response", ""), height=200)
            else:
                st.error(f"识别失败: {result.get('error', '?')}")
                if result.get("raw_response"):
                    st.text_area("模型原始输出", result["raw_response"], height=200)

    # Display OCR results for confirmation
    ocr_data = st.session_state.get("ocr_holdings")
    if ocr_data:
        st.markdown("---")
        st.subheader("识别结果确认")
        st.caption("请核对以下数据，确认无误后点击「导入持仓」。")

        ocr_df = pd.DataFrame(ocr_data)
        edited_ocr = st.data_editor(
            ocr_df, num_rows="dynamic", use_container_width=True,
            hide_index=True,
            column_config={
                "market": st.column_config.SelectboxColumn(options=MARKET_OPTIONS),
            },
        )

        c1, c2 = st.columns(2)
        if c1.button("导入持仓", type="primary", key="ocr_import"):
            portfolio = load_portfolio()
            now = datetime.now(CST).isoformat()
            for _, row in edited_ocr.iterrows():
                sym = str(row.get("symbol", "")).strip()
                if not sym:
                    continue
                h = {
                    "symbol": sym,
                    "name": str(row.get("name", "")),
                    "market": row.get("market", "A"),
                    "source": "ocr",
                    "updated_at": now,
                }
                for k in ("cost_price", "current_price", "quantity", "position_pct"):
                    v = row.get(k)
                    if v and float(v) > 0:
                        h[k] = float(v)
                if ocr_account.strip():
                    h["account"] = ocr_account.strip()
                portfolio.setdefault("holdings", []).append(h)
            save_portfolio(portfolio)
            del st.session_state["ocr_holdings"]
            st.success(f"已导入 {len(edited_ocr)} 条持仓")
            st.rerun()
        if c2.button("清除识别结果", key="ocr_clear"):
            del st.session_state["ocr_holdings"]
            st.rerun()

# ===================================================================
# Tab 3: File Import (CSV / JSON)
# ===================================================================
with tab_upload:
    st.subheader("文件导入")
    st.markdown("""
    **CSV**: 首行表头 `symbol,name,market,cost_price,quantity`（支持中文表头）

    **JSON**: `[{"symbol":"600519","name":"贵州茅台","market":"A"}]`
    """)

    uploaded = st.file_uploader("上传 CSV 或 JSON", type=["csv", "json"],
                                key="file_upload")
    import_account = st.text_input("账户名称（可选）", key="import_account",
                                   placeholder="如：华泰证券")
    merge_mode = st.radio("导入模式", ["追加到现有持仓", "替换全部持仓"],
                          horizontal=True, key="merge_mode")

    if uploaded:
        raw = uploaded.read().decode("utf-8")
        try:
            parsed = (parse_csv_holdings(raw) if uploaded.name.endswith(".csv")
                      else parse_json_holdings(raw))
            if parsed:
                st.write(f"解析到 {len(parsed)} 条:")
                st.dataframe(pd.DataFrame(parsed), use_container_width=True,
                             hide_index=True)
                if st.button("确认导入", type="primary", key="file_import_btn"):
                    if import_account.strip():
                        for h in parsed:
                            h["account"] = import_account.strip()
                    if merge_mode == "替换全部持仓":
                        update_holdings_bulk(parsed)
                    else:
                        p = load_portfolio()
                        existing = p.get("holdings", [])
                        existing.extend(parsed)
                        update_holdings_bulk(existing)
                    st.success(f"已导入 {len(parsed)} 条")
                    st.rerun()
            else:
                st.warning("未解析到有效记录")
        except Exception as e:
            st.error(f"解析失败：{e}")

# ===================================================================
# Tab 4: Table Editor
# ===================================================================
with tab_edit:
    st.subheader("表格编辑")
    st.caption("直接编辑，增删行后点击「同步保存」。")

    edit_data = []
    for h in holdings:
        edit_data.append({
            "代码": h.get("symbol", ""),
            "名称": h.get("name", ""),
            "市场": h.get("market", "A"),
            "账户": h.get("account", "默认"),
            "成本价": h.get("cost_price", 0.0),
            "数量": h.get("quantity", 0),
            "仓位%": h.get("position_pct", 0.0),
        })
    if not edit_data:
        edit_data.append({"代码": "", "名称": "", "市场": "A", "账户": "默认",
                          "成本价": 0.0, "数量": 0, "仓位%": 0.0})

    edited = st.data_editor(
        pd.DataFrame(edit_data), num_rows="dynamic",
        use_container_width=True, hide_index=True,
        column_config={
            "市场": st.column_config.SelectboxColumn(options=MARKET_OPTIONS),
            "成本价": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    if st.button("同步保存", type="primary", key="table_save"):
        new_holdings = []
        for _, row in edited.iterrows():
            sym = str(row.get("代码", "")).strip()
            if not sym:
                continue
            h = {
                "symbol": sym, "name": str(row.get("名称", "")),
                "market": row.get("市场", "A"),
                "source": "manual",
            }
            acct = str(row.get("账户", "")).strip()
            if acct and acct != "默认":
                h["account"] = acct
            for k, cn in [("cost_price", "成本价"), ("quantity", "数量"),
                          ("position_pct", "仓位%")]:
                v = row.get(cn, 0)
                if v and float(v) > 0:
                    h[k] = float(v) if k != "quantity" else int(v)
            new_holdings.append(h)
        update_holdings_bulk(new_holdings)
        ok, msg = validate_portfolio()
        if ok:
            st.success(f"已保存 {len(new_holdings)} 条")
        else:
            st.error(f"校验失败：{msg}")
        st.rerun()
