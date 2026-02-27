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
import pandas as pd

st.set_page_config(page_title="PFA", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user, render_login_page
from agents.secretary_agent import update_holdings_bulk
from pfa.data.store import get_timeline_events, add_timeline_event

inject_v2_theme()

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)


def _render_timeline_view(user_id: str, symbol: str, name: str, in_dialog: bool = False):
    """渲染单标的投资记忆时间轴（建仓原因、AI 建议、异动记录）。in_dialog 时底部显示关闭按钮。"""
    st.markdown(
        f"<div class='pfa-title' style='margin-bottom:8px;'>{escape(name)} 投资记忆</div>",
        unsafe_allow_html=True,
    )
    events = get_timeline_events(user_id, symbol)
    if not events:
        st.markdown(
            '<div class="pfa-card" style="padding:16px; color:#E8EAED;">'
            '<div style="font-size:14px; line-height:1.6;">AI 还没有关于该标的的记忆。</div>'
            '<div style="font-size:13px; color:#9AA0A6; margin-top:8px;">在右侧聊天框告诉我你为什么买入它，或者在下面补充一句备忘，我会帮你写入时间轴。</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        timeline_html = ["<div class='timeline'>"]
        timeline_html.append(
            """
<style>
.timeline { border-left: 2px solid #2D3139; margin: 8px 0 16px 6px; padding-left: 18px; }
.timeline-item { position: relative; margin-bottom: 16px; }
.timeline-item:before { content: ""; position: absolute; left: -21px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background-color: #4285F4; }
.timeline-date { font-size: 12px; color: #9AA0A6; margin-bottom: 4px; }
.timeline-content { font-weight: 600; margin-bottom: 4px; color: #E8EAED; }
.timeline-reason { font-size: 13px; color: #9AA0A6; padding: 8px 10px; background:#242832; border-radius:4px; border: 1px solid #2D3139; }
.timeline-tag { display:inline-block; font-size:11px; padding:2px 6px; border-radius:8px; background:rgba(66,133,244,0.2); color:#4285F4; margin-left:4px; }
</style>
"""
        )
        for ev in events:
            ts = ev.timestamp
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_disp = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts_disp = ts
            tag = ev.event_type.upper()
            timeline_html.append(
                "<div class='timeline-item'>"
                f"<div class='timeline-date'>{escape(ts_disp)}<span class='timeline-tag'>{escape(tag)}</span></div>"
                f"<div class='timeline-content'>{escape(ev.content or '').strip() or '（未填写摘要）'}</div>"
                f"<div class='timeline-reason'>{escape(ev.reasoning or '').strip() or '（暂无详细原因）'}</div>"
                "</div>"
            )
        timeline_html.append("</div>")
        st.markdown("".join(timeline_html), unsafe_allow_html=True)

    st.markdown("---")
    memo = st.text_area(
        "补充一句投资备忘（会写入时间轴）",
        key="timeline_memo_input",
        placeholder="例如：看好业绩反转 / 想观察政策变化后的表现……",
    )
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("写入时间轴", type="primary", key="timeline_add_btn"):
            text = (memo or "").strip()
            if text:
                add_timeline_event(
                    user_id,
                    symbol,
                    {"event_type": "USER_MEMO", "content": text[:60], "reasoning": text},
                )
                st.success("已写入投资记忆")
                st.rerun()
    if in_dialog:
        st.markdown("---")
        if st.button("关闭", key="timeline_dialog_close"):
            if "page" in st.query_params:
                del st.query_params["page"]
            if "symbol" in st.query_params:
                del st.query_params["symbol"]
            st.rerun()


# --- Auth ---
user = get_user()
if not user.get("user_id"):
    render_login_page()
    st.stop()

# --- Load holdings（先加载，以便判断是否进入个股页） ---
# Demo 模式：从引导页「先看看 demo」进入（query_params demo=1）或 session 已标记时，加载示例持仓
if st.query_params.get("demo") == "1":
    st.session_state["pfa_use_demo_portfolio"] = True
demo_mode = st.session_state.get("pfa_use_demo_portfolio", False)
holdings = []
if user.get("mode") == "supabase" and not demo_mode:
    from pfa.data.supabase_store import load_holdings
    _at = user.get("access_token", "")
    holdings = load_holdings(user["user_id"], _at)
else:
    if demo_mode:
        sample_path = ROOT / "config" / "sample-portfolio.json"
        if sample_path.exists():
            with open(sample_path, "r", encoding="utf-8") as f:
                holdings = json.load(f).get("holdings", [])
    else:
        from agents.secretary_agent import load_portfolio
        holdings = load_portfolio().get("holdings", [])

# --- 个股深度：从持仓表点击代码进入 ---
if holdings and st.query_params.get("page") == "ticker" and st.query_params.get("symbol"):
    qsym = st.query_params.get("symbol", "").strip()
    holding = next((x for x in holdings if str(x.get("symbol")) == qsym), None)
    if holding:
        from app.ticker_detail import render_ticker_detail_page
        render_ticker_detail_page(holding, holdings, user)
        st.stop()

render_topnav(active="portfolio", user_email=user.get("email", ""))

# --- 时间轴：表格内 🕒 点击用 st.dialog 弹窗（无 dialog 时 fallback 整页） ---
if holdings and st.query_params.get("page") == "timeline" and st.query_params.get("symbol"):
    qsym = st.query_params.get("symbol", "").strip()
    holding = next((x for x in holdings if str(x.get("symbol")) == qsym), None)
    if holding:
        uid = user.get("user_id") or "admin"
        sym = str(holding.get("symbol", ""))
        name = holding.get("name", sym)
        if hasattr(st, "dialog"):
            @st.dialog(f"{name} 投资记忆")
            def _timeline_dialog():
                _render_timeline_view(uid, sym, name, in_dialog=True)

            _timeline_dialog()
        else:
            render_topnav(active="portfolio", user_email=user.get("email", ""))
            _render_timeline_view(uid, sym, name, in_dialog=False)
            st.stop()

# Demo 模式提示条（深色卡片，禁止白底灰字）
if demo_mode:
    dc1, dc2 = st.columns([6, 1])
    with dc1:
        st.markdown(
            '<div class="pfa-card" style="padding:12px 16px; margin-bottom:12px; display:flex; align-items:center; gap:8px;">'
            '<span style="font-size:14px; color:#E8EAED;">📺 演示模式：正在使用示例持仓，你的修改不会保存。</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with dc2:
        if st.button("退出 demo", key="exit_demo"):
            st.session_state.pop("pfa_use_demo_portfolio", None)
            st.rerun()

    # 已移除首页浮动引导提示，避免遮挡核心视图

def _save_holdings(new_list):
    """统一的持仓保存入口：支持 Supabase / 本地模式。Demo 模式下不持久化。"""
    if not new_list:
        return
    if demo_mode:
        return  # 演示模式不写入
    if user.get("mode") == "supabase":
        from pfa.data.supabase_store import load_holdings as lh, save_holdings as sh
        _at = user.get("access_token", "")
        sh(user["user_id"], lh(user["user_id"], _at) + new_list, _at)
    else:
        from agents.secretary_agent import add_holding
        for h in new_list:
            add_holding(
                h.get("symbol", ""),
                h.get("name", ""),
                h.get("market", "A"),
                h.get("cost_price", 0),
                h.get("quantity", 0),
                0,
                h.get("source", "manual"),
            )

# ===================================================================
# 空状态：左侧友好引导 + 右侧 AI 迎宾与快捷录入（对话驱动，无大表格压迫）
# ===================================================================
if not holdings:
    minimal_val = {
        "total_value_cny": 0, "total_pnl_cny": 0, "total_pnl_pct": 0,
        "holding_count": 0, "account_count": 0, "by_account": {},
    }
    col_left, col_right = st.columns([2, 3])  # 右侧 AI 占比更大
    with col_left:
        st.markdown("""
        <div class="pfa-card" style="text-align:center; padding:48px 24px;">
            <div style="font-size:48px; margin-bottom:16px;">📊</div>
            <div class="pfa-title" style="margin-bottom:12px;">暂无持仓数据</div>
            <div class="pfa-body" style="color:#9AA0A6; line-height:1.6;">
                请通过右侧助理上传您的券商截图或账单，或直接对助理说「我买了 100 股苹果」，开启智能财富管理。
            </div>
        </div>""", unsafe_allow_html=True)
    with col_right:
        render_expert_chat(holdings=[], val=minimal_val, user=user, save_holdings=_save_holdings, is_empty_state=True)
    if st.session_state.get("pfa_rerun_after_add"):
        del st.session_state["pfa_rerun_after_add"]
        st.rerun()
    st.stop()

# ===================================================================
# PORTFOLIO HUB (has holdings)
# ===================================================================
from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
from app.charts import render_allocation_pie, render_pnl_waterfall

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

# --- Exception Banner (Top1)：点击进入个股分析页 ---
exceptions = []
for h in all_holdings_flat:
    pct = abs(h.get("today_chg_pct", 0))
    if pct >= 3:
        icon = "🔴" if h["today_chg_pct"] < 0 else "📈"
        label = f'{icon} {h.get("name","")[:4]} {h["today_chg_pct"]:+.1f}%'
        exceptions.append({"symbol": h.get("symbol", ""), "label": label, "up": "📈" in label})

if exceptions:
    badges_html = "".join(
        f'<a href="/?page=ticker&symbol={escape(str(e["symbol"]))}" style="text-decoration:none;">'
        f'<span class="mover-badge {"up" if e["up"] else "down"}">{escape(e["label"])}</span></a>'
        for e in exceptions[:8]
    )
    st.markdown(f"""
<div class="chart-panel" style="margin-bottom:16px;">
    <div class="chart-panel-title">⚡ 今日异动</div>
    <div class="chart-panel-body">
        <div class="market-movers">
            <span class="pfa-caption" style="margin-right:8px;">涨跌 ≥3%</span>
            {badges_html}
        </div>
    </div>
</div>""", unsafe_allow_html=True)

# --- Metrics (Top4: Chinese terms) ---
update_time = ""
for h in all_holdings_flat:
    t = h.get("update_time", "")
    if t and len(t) > len(update_time):
        update_time = t

c1, c2, c3, c4 = st.columns(4)
# 迷你趋势图占位（7 点，后续可接真实 7 日数据）
spark_up = '<div class="sparkline"><svg viewBox="0 0 64 20" preserveAspectRatio="none"><polyline fill="none" stroke="#4285F4" stroke-width="1" points="0,14 10,12 22,10 34,8 44,6 54,4 64,2"/></svg></div>'
spark_dn = '<div class="sparkline"><svg viewBox="0 0 64 20" preserveAspectRatio="none"><polyline fill="none" stroke="#5F6368" stroke-width="1" points="0,4 10,6 22,8 34,10 44,12 54,14 64,16"/></svg></div>'
c1.markdown(f'<div class="metric-card"><div class="label">总资产</div><div class="value">¥{total_v:,.0f}</div>{spark_up}</div>', unsafe_allow_html=True)

today_c = COLORS["up"] if total_today_pnl >= 0 else COLORS["down"]
ts = "+" if total_today_pnl >= 0 else ""
c2_spark = spark_up if total_today_pnl >= 0 else spark_dn
c2.markdown(f'<div class="metric-card"><div class="label">今日盈亏</div><div class="value" style="color:{today_c};">{ts}¥{total_today_pnl:,.0f}</div>{c2_spark}</div>', unsafe_allow_html=True)

c3.markdown(f'<div class="metric-card"><div class="label">累计盈亏</div><div class="value" style="color:{pnl_c};">{sign}¥{total_pnl:,.0f}</div><div class="change" style="color:{pnl_c};">{sign}{total_pct:.2f}%</div></div>', unsafe_allow_html=True)

c4.markdown(f'<div class="metric-card"><div class="label">{val["holding_count"]} 只标的 · {val["account_count"]} 个账户</div><div class="value" style="font-size:12px;font-weight:500;color:#5F6368;">更新: {update_time[-8:] if update_time else "—"}</div></div>', unsafe_allow_html=True)

# --- Main: 持仓中心制 — 表格全宽 + 下方图表 ---
st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)

# 持仓明细：用 expander 收纳，避免无限拉长；表格占据 100% 页面宽度
edit_mode = st.session_state.get("holdings_edit_mode", False)
with st.expander("**持仓明细**" + (" · 编辑中" if edit_mode else ""), expanded=True):
    row_btn = st.columns([1])[0]
    with row_btn:
        if st.button("编辑" if not edit_mode else "取消", key="holdings_toggle_edit"):
            st.session_state["holdings_edit_mode"] = not edit_mode
            st.rerun()

    if st.session_state.get("holdings_edit_mode"):
        if demo_mode:
            st.markdown(
                '<div class="pfa-card" style="padding:12px 16px; margin-bottom:12px; font-size:14px; color:#E8EAED;">'
                'Demo 模式下不可编辑持仓，请退出 demo 后配置真实持仓。</div>',
                unsafe_allow_html=True,
            )
        elif user.get("mode") == "supabase":
            st.markdown(
                '<div class="pfa-card" style="padding:12px 16px; margin-bottom:12px; font-size:14px; color:#E8EAED;">'
                'Supabase 模式下请使用右侧助理或后台修改持仓。</div>',
                unsafe_allow_html=True,
            )
        else:
            from agents.secretary_agent import load_portfolio, save_portfolio
            # 原地编辑：深色表头 + 成本/数量为透明底线输入框 + 行末垃圾桶
            st.markdown('<div id="pfa-holdings-edit" class="pfa-edit-table"></div>', unsafe_allow_html=True)
            with st.container():
                # 表头
                hc0, hc1, hc2, hc3, hc4, hc5, hc6 = st.columns(7)
                for c, label in [(hc0, "账户"), (hc1, "代码"), (hc2, "名称"), (hc3, "市场"), (hc4, "成本"), (hc5, "数量"), (hc6, "")]:
                    with c:
                        st.caption(label if label else "操作")
                # 初始化 session 默认值（按行索引保证多账户同代码时 key 唯一）
                for idx, h in enumerate(holdings):
                    sym = str(h.get("symbol", ""))
                    if not sym:
                        continue
                    if f"edit_cost_{idx}" not in st.session_state:
                        st.session_state[f"edit_cost_{idx}"] = str(h.get("cost_price") or "").strip() or "0"
                    if f"edit_qty_{idx}" not in st.session_state:
                        st.session_state[f"edit_qty_{idx}"] = str(h.get("quantity") or "").strip() or "0"
                # 数据行
                to_remove_idx = None
                for idx, h in enumerate(holdings):
                    sym = str(h.get("symbol", ""))
                    if not sym:
                        continue
                    c0, c1, c2, c3, c4, c5, c6 = st.columns(7)
                    with c0:
                        st.text(h.get("account", "默认"))
                    with c1:
                        st.text(sym)
                    with c2:
                        st.text((h.get("name") or "")[:12])
                    with c3:
                        st.text(h.get("market", "A"))
                    with c4:
                        st.text_input("成本", key=f"edit_cost_{idx}", label_visibility="collapsed")
                    with c5:
                        st.text_input("数量", key=f"edit_qty_{idx}", label_visibility="collapsed")
                    with c6:
                        if st.button("🗑️", key=f"holdings_del_{idx}", help="删除该行"):
                            to_remove_idx = idx
                if to_remove_idx is not None:
                    p = load_portfolio()
                    p["holdings"] = [x for i, x in enumerate(p.get("holdings", [])) if i != to_remove_idx]
                    save_portfolio(p)
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_cost_") or k.startswith("edit_qty_") or k.startswith("holdings_del_"):
                            del st.session_state[k]
                    st.rerun()
            if st.button("保存修改", type="primary", key="holdings_save"):
                out = []
                for idx, h in enumerate(holdings):
                    sym = str(h.get("symbol", "")).strip()
                    if not sym:
                        continue
                    try:
                        cost = float(st.session_state.get(f"edit_cost_{idx}", "0") or "0")
                    except (ValueError, TypeError):
                        cost = 0
                    try:
                        qty = float(st.session_state.get(f"edit_qty_{idx}", "0") or "0")
                    except (ValueError, TypeError):
                        qty = 0
                    out.append({
                        "symbol": sym,
                        "name": str(h.get("name", "")).strip(),
                        "market": str(h.get("market", "A")),
                        "account": str(h.get("account", "")).strip() or "默认",
                        "cost_price": cost,
                        "quantity": qty,
                        "source": h.get("source", "manual"),
                    })
                update_holdings_bulk(out)
                for k in list(st.session_state.keys()):
                    if k.startswith("edit_cost_") or k.startswith("edit_qty_"):
                        del st.session_state[k]
                st.session_state["holdings_edit_mode"] = False
                st.success("已保存")
                st.rerun()
    else:
        tbl = '<table class="fin-table"><thead><tr>'
        for c in ["标的", "现价", "今日", "成本", "数量", "市值", "仓位", "累计盈亏", "收益率"]:
            align = ' class="r"' if c != "标的" else ""
            tbl += f"<th{align}>{c}</th>"
        tbl += "</tr></thead><tbody>"
        for acct_name, acct_data in val["by_account"].items():
            tbl += f'<tr class="group-row"><td colspan="9">{escape(acct_name)} · ¥{acct_data["value"]:,.0f}</td></tr>'
            for h in acct_data["holdings"]:
                pnl, pct = h["pnl_cny"], h["pnl_pct"]
                cls = "up" if pnl >= 0 else "down"
                ps = "+" if pnl >= 0 else ""
                tp, tc = h.get("today_pnl", 0), "up" if h.get("today_pnl", 0) >= 0 else "down"
                tps = "+" if tp >= 0 else ""
                w = h.get("weight_pct", 0)
                w_style = f'color:{COLORS["up"]};font-weight:700;' if w > 30 else ""
                sym = escape(str(h.get("symbol", "")))
                name = escape(str(h.get("name", ""))[:18])
                timeline_link = f"/?page=timeline&symbol={sym}"
                today_chg = h.get("today_chg_pct") or 0
                tags_html = ""
                if abs(today_chg) >= 3:
                    tags_html += '<span class="ai-tag hot">🔥 异动中</span>'
                if pct > 50:
                    tags_html += '<span class="ai-tag high">📉 估值过高</span>'
                symbol_cell = (
                    f'<div class="cell-symbol"><a class="ticker-badge sym" href="/?page=ticker&symbol={sym}">{sym}</a></div>'
                    f'<div class="cell-name">{name} <a href="{timeline_link}" class="timeline-link" title="查看投资记忆">🕒</a>{tags_html}</div>'
                )
                tbl += (
                    "<tr>"
                    f'<td class="symbol-cell">{symbol_cell}</td>'
                    f'<td class="r">{h.get("current_price","—")}</td>'
                    f'<td class="r {tc}">{tps}{tp:,.0f}</td>'
                    f'<td class="r muted">{h.get("cost_price","—")}</td>'
                    f'<td class="r">{h.get("quantity","—")}</td>'
                    f'<td class="r">¥{h["value_cny"]:,.0f}</td>'
                    f'<td class="r" style="{w_style}">{w:.1f}%</td>'
                    f'<td class="r {cls}">{ps}{pnl:,.0f}</td>'
                    f'<td class="r {cls}">{ps}{pct:.1f}%</td>'
                    "</tr>"
                )
        tbl += "</tbody></table>"
        st.markdown(tbl, unsafe_allow_html=True)

# 图表：仓位分布 + 今日盈亏（收纳在表格下方）
st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
ch1, ch2 = st.columns(2)
with ch1:
    st.markdown('<div class="chart-panel"><div class="chart-panel-title">仓位分布</div></div>', unsafe_allow_html=True)
    render_allocation_pie(all_holdings_flat, total_v)
with ch2:
    st.markdown('<div class="chart-panel"><div class="chart-panel-title">今日盈亏贡献</div></div>', unsafe_allow_html=True)
    render_pnl_waterfall(all_holdings_flat)

