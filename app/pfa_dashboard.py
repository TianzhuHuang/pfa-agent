"""
PFA v2 — Portfolio Hub (基金经理级)

Exception-Driven: 今日异常 → 持仓概览 → AI 助理
"""

import sys, json, os
from pathlib import Path

# 加载 .env（项目根目录）
ROOT = Path(__file__).resolve().parent.parent
_env = ROOT / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)

from datetime import datetime, timedelta, timezone
from html import escape

sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="PFA", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

from app.theme_v2 import inject_v2_theme, render_topnav, COLORS
from app.auth_v2 import get_user, render_login_page
from agents.secretary_agent import load_portfolio, update_holdings_bulk
from pfa.data.store import get_timeline_events, add_timeline_event
from app.ai_expert import render_analysis_chat

inject_v2_theme()

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)


def _append_holdings_for_quick_entry(new_holdings):
    """用于「录入持仓」弹窗：在现有持仓基础上追加新记录，不覆盖其它账户。"""
    if not new_holdings:
        return
    p = load_portfolio()
    base = p.get("holdings", [])
    # 先拼接，再走 update_holdings_bulk 做统一清洗
    merged = base + list(new_holdings)
    update_holdings_bulk(merged)


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
.timeline-tag { display:inline-block; font-size:12px; padding:2px 6px; border-radius:8px; background:rgba(66,133,244,0.2); color:#4285F4; margin-left:4px; }
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

# FAB 点击：通过 session_state 打开右侧抽屉对话（不跳转页面）
# 兼容旧链接 ?open_pfa_chat=1
if st.query_params.get("open_pfa_chat") == "1" and user.get("user_id"):
    st.session_state["open_global_chat"] = True
    if "open_pfa_chat" in st.query_params:
        del st.query_params["open_pfa_chat"]
    st.rerun()

# 已登录时右上角固定显示：编辑持仓 + 录入持仓 + 退出（Portfolio 页全部显示，其他页仅录入+退出）
render_topnav(
    active="portfolio",
    user_email=user.get("email") or ("已登录" if user.get("user_id") else ""),
    show_edit_holdings=not demo_mode,  # 有持仓时始终显示编辑，Supabase 模式下 expander 内会提示
)

# API Key 缺失提示：仅当未配置时显示，不阻塞使用
if not os.environ.get("DASHSCOPE_API_KEY") and user.get("user_id"):
    st.markdown(
        '<div class="pfa-card" style="padding:10px 16px; margin-bottom:12px; font-size:13px; color:#9AA0A6; '
        'border-left:3px solid #FB8C00;">'
        '💡 未配置 DASHSCOPE_API_KEY，AI 对话与深度分析不可用。'
        '在项目根目录创建 <code>.env</code> 并添加 <code>DASHSCOPE_API_KEY=sk-xxx</code> 后重启。</div>',
        unsafe_allow_html=True,
    )

# 顶部「录入持仓」快捷入口：右侧统一风格弹窗
if st.session_state.get("open_holdings_entry") and hasattr(st, "dialog"):
    from app.ai_expert import _render_quick_entry  # 复用已有的录入模块

    @st.dialog("录入持仓")
    def _entry_dialog():
        st.markdown(
            "<div class='pfa-caption' style='margin-bottom:12px;font-size:14px;color:#9AA0A6;line-height:1.5;'>"
            "选择一种方式快速录入你的持仓，支持截图 OCR、CSV/JSON 文件以及代码搜索。</div>",
            unsafe_allow_html=True,
        )
        _render_quick_entry(_append_holdings_for_quick_entry, user)

    _entry_dialog()

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
            render_topnav(active="portfolio", user_email=user.get("email") or ("已登录" if user.get("user_id") else ""))
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
                截图你的持仓 → 点击右上角的「录入持仓」按钮，可以直接识别截图持仓明细内容
            </div>
        </div>""", unsafe_allow_html=True)
    with col_right:
        render_analysis_chat(holdings=[], val=minimal_val, user=user)
    if st.session_state.get("pfa_rerun_after_add"):
        del st.session_state["pfa_rerun_after_add"]
        st.rerun()
    st.stop()

# ===================================================================
# PORTFOLIO HUB (has holdings)
# ===================================================================
from pfa.portfolio_valuation import calculate_portfolio_value, get_fx_rates, get_realtime_prices
from app.charts import render_allocation_pie, render_pnl_waterfall

try:
    fx = get_fx_rates()
    prices = get_realtime_prices(holdings)
    val = calculate_portfolio_value(holdings, prices, fx)
except Exception:
    _fallback_holdings = []
    for h in holdings:
        hc = dict(h)
        hc.setdefault("current_price", 0)
        hc.setdefault("pnl_cny", 0)
        hc.setdefault("pnl_pct", 0)
        hc.setdefault("value_cny", 0)
        _fallback_holdings.append(hc)
    val = {
        "total_value_cny": 0, "total_pnl_cny": 0, "total_pnl_pct": 0,
        "holding_count": len(holdings), "account_count": 1,
        "by_account": {"默认": {"holdings": _fallback_holdings, "value_cny": 0}},
    }
    st.toast("行情数据暂不可用，请稍后刷新", icon="⚠️")

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

# --- Metrics：Stake 风格 Total Wealth 头部 ---
update_time = ""
for h in all_holdings_flat:
    t = h.get("update_time", "")
    if t and len(t) > len(update_time):
        update_time = t

# 货币换算：统一按选定币种展示（Total Wealth 与持仓表格共用）
fx_rates = val.get("fx_rates") or get_fx_rates()
if "display_currency" not in st.session_state:
    st.session_state["display_currency"] = "CNY"
ccy = st.session_state["display_currency"]
ccy_factor = 1.0 / fx_rates.get(ccy, 1.0) if ccy != "CNY" else 1.0
ccy_symbol = {"CNY": "¥", "USD": "$", "HKD": "HK$"}.get(ccy, "¥")

col_main, col_side = st.columns([3, 1])

day_sign = "+" if total_today_pnl >= 0 else ""
day_color = COLORS["up"] if total_today_pnl >= 0 else COLORS["down"]
total_sign = "+" if total_pnl >= 0 else ""
total_color = COLORS["up"] if total_pnl >= 0 else COLORS["down"]

col_main.markdown(
    f"""
<div class="metric-card stake-equity">
  <div class="label">Total Wealth</div>
  <div class="value">{ccy_symbol}{total_v * ccy_factor:,.0f}</div>
  <div class="change-lines">
    <div class="change-line">
      <span class="arrow {'up' if total_today_pnl >= 0 else 'down'}"></span>
      <span class="text">今日
        <span class="num" style="color:{day_color};">{day_sign}{ccy_symbol}{total_today_pnl * ccy_factor:,.0f}</span>
      </span>
    </div>
    <div class="change-line">
      <span class="arrow {'up' if total_pnl >= 0 else 'down'}"></span>
      <span class="text">累计
        <span class="num" style="color:{total_color};">{total_sign}{ccy_symbol}{total_pnl * ccy_factor:,.0f} ({total_sign}{total_pct:.2f}%)</span>
      </span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

col_side.markdown(
    f"""
<div class="metric-card stake-summary">
  <div class="label">Overview</div>
  <div class="value" style="font-size:16px;">{val["holding_count"]} 只标的 · {val["account_count"]} 个账户</div>
  <div class="change" style="font-size:12px;color:#9AA0A6;">更新: {update_time[-8:] if update_time else "—"}</div>
</div>
""",
    unsafe_allow_html=True,
)

# --- Main: 持仓中心制 — 表格全宽 + 下方图表 ---
st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)

# 持仓明细：标题行 + 币种筛选（轻量，放右侧）
edit_mode = st.session_state.get("holdings_edit_mode", False)
exp_col, ccy_col = st.columns([1, 0.08])
with exp_col:
    with st.expander("**持仓明细**" + (" · 编辑中" if edit_mode else ""), expanded=True):
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
                # 表头行：列名 + 保存修改 / 取消
                head_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 0.6])
                for c, label in [(head_cols[0], "账户"), (head_cols[1], "代码"), (head_cols[2], "名称"), (head_cols[3], "市场"), (head_cols[4], "成本"), (head_cols[5], "数量"), (head_cols[6], "操作")]:
                    with c:
                        st.caption(label)
                with head_cols[7]:
                    b1, b2 = st.columns(2)
                    with b1:
                        save_clicked = st.button("保存修改", type="primary", key="holdings_save")
                    with b2:
                        cancel_clicked = st.button("取消", key="holdings_cancel")
                if cancel_clicked:
                    st.session_state["holdings_edit_mode"] = False
                    st.rerun()
                # 原地编辑表格体
                st.markdown('<div id="pfa-holdings-edit" class="pfa-edit-table"></div>', unsafe_allow_html=True)
                with st.container():
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
                if save_clicked:
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
            # 只读模式：表格带 thead；编辑按钮在 expander 外与「持仓明细」并排
            tbl = '<table class="fin-table"><thead><tr>'
            for c in ["标的", "现价", "今日", "成本", "数量", "市值", "仓位", "累计盈亏", "收益率"]:
                align = ' class="r"' if c != "标的" else ""
                tbl += f"<th{align}>{c}</th>"
            tbl += "</tr></thead><tbody>"
            for acct_name, acct_data in val["by_account"].items():
                acct_val = acct_data["value"] * ccy_factor
                tbl += f'<tr class="group-row"><td colspan="9">{escape(acct_name)} · {ccy_symbol}{acct_val:,.0f}</td></tr>'
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
                    val_display = h["value_cny"] * ccy_factor
                    pnl_display = pnl * ccy_factor
                    tp_display = tp * ccy_factor
                    symbol_cell = (
                        f'<div class="cell-symbol"><a class="ticker-badge sym" href="/?page=ticker&symbol={sym}">{sym}</a></div>'
                        f'<div class="cell-name">{name} <a href="{timeline_link}" class="timeline-link" title="查看投资记忆">🕒</a>{tags_html}</div>'
                    )
                    tbl += (
                        "<tr>"
                        f'<td class="symbol-cell">{symbol_cell}</td>'
                        f'<td class="r">{h.get("current_price","—")}</td>'
                        f'<td class="r {tc}">{tps}{tp_display:,.0f}</td>'
                        f'<td class="r muted">{h.get("cost_price","—")}</td>'
                        f'<td class="r">{h.get("quantity","—")}</td>'
                        f'<td class="r">{ccy_symbol}{val_display:,.0f}</td>'
                        f'<td class="r" style="{w_style}">{w:.1f}%</td>'
                        f'<td class="r {cls}">{ps}{pnl_display:,.0f}</td>'
                        f'<td class="r {cls}">{ps}{pct:.1f}%</td>'
                        "</tr>"
                    )
            tbl += "</tbody></table>"
            st.markdown(tbl, unsafe_allow_html=True)

with ccy_col:
    st.markdown('<div class="pfa-caption ccy-selector-label" style="font-size:12px;color:#5F6368;margin-bottom:4px;">币种</div>', unsafe_allow_html=True)
    ccy_options = ["CNY", "USD", "HKD"]
    sel = st.selectbox(
        "币种",
        ccy_options,
        index=ccy_options.index(ccy) if ccy in ccy_options else 0,
        key="display_currency_sel",
        label_visibility="collapsed",
    )
    if sel != ccy:
        st.session_state["display_currency"] = sel
        st.rerun()

# 图表：仓位分布 + 今日盈亏（收纳在表格下方）
st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
ch1, ch2 = st.columns(2)
with ch1:
    # 仓位分布：默认总资产，标题行右侧下拉按账户筛选
    account_names = sorted(val["by_account"].keys())
    allocation_options = ["总资产"] + account_names
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    row1, row2 = st.columns([2, 1])
    with row1:
        st.markdown('<div class="chart-panel-title">仓位分布</div>', unsafe_allow_html=True)
    with row2:
        alloc_sel = st.selectbox(
            "按账户",
            allocation_options,
            index=0,
            key="allocation_chart_account",
            label_visibility="collapsed",
        )
    if alloc_sel == "总资产":
        _pie_holdings = all_holdings_flat
        _pie_total = total_v
    else:
        _pie_holdings = val["by_account"][alloc_sel]["holdings"]
        _pie_total = val["by_account"][alloc_sel]["value"]
    render_allocation_pie(_pie_holdings, _pie_total, ccy_symbol=ccy_symbol, ccy_factor=ccy_factor)
    st.markdown('</div>', unsafe_allow_html=True)
with ch2:
    st.markdown('<div class="chart-panel"><div class="chart-panel-title">今日盈亏贡献</div></div>', unsafe_allow_html=True)
    render_pnl_waterfall(all_holdings_flat, ccy_symbol=ccy_symbol, ccy_factor=ccy_factor)

# 页面底部：清空持仓（测试用，仅本地模式）
if not demo_mode and user.get("mode") != "supabase":
    st.markdown("---")
    if st.button("清空持仓（测试用）", key="clear_holdings_btn", help="清空所有持仓数据，便于重新测试录入流程"):
        update_holdings_bulk([])
        st.success("已清空持仓")
        st.rerun()

if st.session_state.get("open_global_chat") and hasattr(st, "dialog"):
    @st.dialog("PFA 思考")
    def _global_pfa_chat():
        render_analysis_chat(holdings, val, user)

    _global_pfa_chat()

# 雪球式 FAB：Streamlit 按钮触发，当前页弹出右侧抽屉（不跳转、不新开标签）
if user.get("user_id"):
    with st.form(key="pfa_fab_form", clear_on_submit=False):
        _submitted = st.form_submit_button("问问投资的问题吧，帮你发现投资好机会")
    if _submitted:
        st.session_state["open_global_chat"] = True
        st.rerun()
