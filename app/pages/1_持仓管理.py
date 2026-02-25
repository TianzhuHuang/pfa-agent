"""持仓管理 — 手动录入 / 批量导入 / 编辑 / 同步"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from agents.secretary_agent import (
    load_portfolio, save_portfolio, validate_portfolio,
    add_holding, remove_holding, update_holdings_bulk,
    parse_csv_holdings, parse_json_holdings,
)

MARKET_OPTIONS = ["A", "HK", "US", "OTHER"]

st.header("持仓管理")

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

# --- Current Holdings ---
st.subheader("当前持仓")
if holdings:
    df = pd.DataFrame(holdings)
    cols = [c for c in ["symbol", "name", "market", "cost_price",
                        "quantity", "position_pct", "source"] if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    st.caption(f"共 {len(holdings)} 个标的")
else:
    st.info("暂无持仓。请通过下方方式添加。")

st.markdown("---")

# --- Tab layout: manual / upload / edit ---
tab_add, tab_upload, tab_edit = st.tabs(["手动添加", "批量导入", "表格编辑"])

# --- Tab 1: Manual single entry ---
with tab_add:
    st.subheader("手动添加标的")
    with st.form("add_single", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        symbol = c1.text_input("代码", placeholder="600519")
        name = c2.text_input("名称", placeholder="贵州茅台")
        market = c3.selectbox("市场", MARKET_OPTIONS)

        c4, c5, c6 = st.columns(3)
        cost_price = c4.number_input("成本价", min_value=0.0, step=0.01, format="%.2f")
        quantity = c5.number_input("数量（股）", min_value=0, step=100)
        position_pct = c6.number_input("仓位 %", min_value=0.0, max_value=100.0, step=1.0)

        if st.form_submit_button("添加", type="primary"):
            if not symbol.strip():
                st.error("代码不能为空")
            else:
                add_holding(symbol, name, market, cost_price, int(quantity), position_pct)
                st.success(f"已添加 {name or symbol}")
                st.rerun()

# --- Tab 2: Batch upload (CSV / JSON) ---
with tab_upload:
    st.subheader("批量导入")
    st.markdown("""
    **CSV 格式**：首行表头 `symbol,name,market,cost_price,quantity`（或中文：代码,名称,市场,成本价,数量）

    **JSON 格式**：数组 `[{"symbol":"600519","name":"贵州茅台","market":"A"}]` 或 `{"holdings":[...]}`
    """)

    uploaded = st.file_uploader("上传 CSV 或 JSON 文件", type=["csv", "json"])
    merge_mode = st.radio("导入模式", ["追加到现有持仓", "替换全部持仓"], horizontal=True)

    if uploaded:
        raw = uploaded.read().decode("utf-8")
        try:
            if uploaded.name.endswith(".csv"):
                parsed = parse_csv_holdings(raw)
            else:
                parsed = parse_json_holdings(raw)

            if parsed:
                st.write(f"解析到 {len(parsed)} 条记录：")
                st.dataframe(pd.DataFrame(parsed), use_container_width=True, hide_index=True)

                if st.button("确认导入", type="primary"):
                    if merge_mode == "替换全部持仓":
                        update_holdings_bulk(parsed)
                    else:
                        portfolio = load_portfolio()
                        existing = portfolio.get("holdings", [])
                        existing_syms = {h["symbol"] for h in existing}
                        for h in parsed:
                            if h.get("symbol") not in existing_syms:
                                existing.append(h)
                        update_holdings_bulk(existing)
                    ok, msg = validate_portfolio()
                    if ok:
                        st.success(f"导入成功，共 {len(parsed)} 条")
                    else:
                        st.warning(f"已导入但校验有警告：{msg}")
                    st.rerun()
            else:
                st.warning("未解析到有效记录")
        except Exception as e:
            st.error(f"解析失败：{e}")

# --- Tab 3: Full table editor ---
with tab_edit:
    st.subheader("表格编辑")
    st.caption("直接编辑下方表格，增删行后点击「同步保存」。")

    edit_data = []
    for h in holdings:
        edit_data.append({
            "代码": h.get("symbol", ""),
            "名称": h.get("name", ""),
            "市场": h.get("market", "A"),
            "成本价": h.get("cost_price", 0.0),
            "数量": h.get("quantity", 0),
            "仓位%": h.get("position_pct", 0.0),
        })
    if not edit_data:
        edit_data.append({"代码": "", "名称": "", "市场": "A",
                          "成本价": 0.0, "数量": 0, "仓位%": 0.0})

    edited = st.data_editor(
        pd.DataFrame(edit_data), num_rows="dynamic",
        use_container_width=True, hide_index=True,
        column_config={
            "市场": st.column_config.SelectboxColumn(options=MARKET_OPTIONS),
            "成本价": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    if st.button("同步保存到 my-portfolio.json", type="primary"):
        new_holdings = []
        for _, row in edited.iterrows():
            sym = str(row.get("代码", "")).strip()
            if not sym:
                continue
            new_holdings.append({
                "symbol": sym, "name": str(row.get("名称", "")),
                "market": row.get("市场", "A"),
                "cost_price": float(row.get("成本价", 0)),
                "quantity": int(row.get("数量", 0)),
                "position_pct": float(row.get("仓位%", 0)),
            })
        update_holdings_bulk(new_holdings)
        ok, msg = validate_portfolio()
        if ok:
            st.success(f"已保存 {len(new_holdings)} 条持仓")
        else:
            st.error(f"校验失败：{msg}")
        st.rerun()
