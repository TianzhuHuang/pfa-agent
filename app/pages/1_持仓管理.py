"""持仓管理页 — 查看 / 编辑 / 校验持仓标的"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

PORTFOLIO_PATH = ROOT / "config" / "my-portfolio.json"
SCHEMA_PATH = ROOT / "config" / "user-profile.schema.json"
MARKET_OPTIONS = ["A", "HK", "US", "OTHER"]
SOURCE_OPTIONS = ["manual", "ocr", "browser", "excel"]
CST = timezone(timedelta(hours=8))


def load_portfolio() -> dict:
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "holdings": [], "channels": {}, "preferences": {}}


def save_portfolio(data: dict) -> None:
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_portfolio() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_portfolio.py"),
         str(PORTFOLIO_PATH)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return result.returncode == 0, result.stdout + result.stderr


# --- Page ---
st.header("持仓管理")

portfolio = load_portfolio()
holdings = portfolio.get("holdings", [])

st.subheader("当前持仓")

if holdings:
    df = pd.DataFrame(holdings)
    display_cols = [c for c in ["symbol", "name", "market", "source",
                                "cost_price", "quantity", "position_pct"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("暂无持仓数据。请在下方添加。")

st.markdown("---")
st.subheader("编辑持仓")

with st.form("edit_holdings", clear_on_submit=False):
    st.markdown("在下方表格中编辑持仓（可增删改行），完成后点击 **同步** 按钮。")

    edit_data = []
    for h in holdings:
        edit_data.append({
            "symbol": h.get("symbol", ""),
            "name": h.get("name", ""),
            "market": h.get("market", "A"),
            "source": h.get("source", "manual"),
            "cost_price": h.get("cost_price", 0.0),
            "quantity": h.get("quantity", 0),
        })
    if not edit_data:
        edit_data.append({
            "symbol": "", "name": "", "market": "A",
            "source": "manual", "cost_price": 0.0, "quantity": 0,
        })

    edited_df = st.data_editor(
        pd.DataFrame(edit_data),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "symbol": st.column_config.TextColumn("代码", help="如 600519, AAPL, 00883"),
            "name": st.column_config.TextColumn("名称", help="标的名称"),
            "market": st.column_config.SelectboxColumn("市场", options=MARKET_OPTIONS),
            "source": st.column_config.SelectboxColumn("来源", options=SOURCE_OPTIONS),
            "cost_price": st.column_config.NumberColumn("成本价", min_value=0, format="%.2f"),
            "quantity": st.column_config.NumberColumn("数量", min_value=0),
        },
        hide_index=True,
    )

    submitted = st.form_submit_button("同步到 my-portfolio.json", type="primary")

if submitted:
    new_holdings = []
    for _, row in edited_df.iterrows():
        sym = str(row.get("symbol", "")).strip()
        if not sym:
            continue
        h = {
            "symbol": sym,
            "name": str(row.get("name", "")).strip(),
            "market": row.get("market", "A"),
            "source": row.get("source", "manual"),
            "updated_at": datetime.now(CST).isoformat(),
        }
        cp = row.get("cost_price", 0)
        if cp and float(cp) > 0:
            h["cost_price"] = float(cp)
        qty = row.get("quantity", 0)
        if qty and int(qty) > 0:
            h["quantity"] = int(qty)
        new_holdings.append(h)

    portfolio["holdings"] = new_holdings
    save_portfolio(portfolio)

    ok, msg = validate_portfolio()
    if ok:
        st.success(f"已保存 {len(new_holdings)} 条持仓并通过 Schema 校验。")
        st.code(msg, language="text")
    else:
        st.error("Schema 校验未通过，请检查数据：")
        st.code(msg, language="text")

    st.rerun()
