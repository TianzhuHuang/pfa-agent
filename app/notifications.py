"""
消息中心 (Notification Center)

集中展示: 晨报摘要 + 异动预警 + 系统通知
嵌入对话: 预警和晨报可以在 AI Expert 聊天中直接展开
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import streamlit as st

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CST = timezone(timedelta(hours=8))


def _get_unread_count() -> int:
    """Get number of unread notifications."""
    notifs = st.session_state.get("notifications", [])
    return sum(1 for n in notifs if not n.get("read"))


def add_notification(ntype: str, title: str, body: str, severity: str = "info"):
    """Add a notification to the center."""
    if "notifications" not in st.session_state:
        st.session_state["notifications"] = []

    st.session_state["notifications"].insert(0, {
        "type": ntype,  # alert / briefing / system
        "title": title,
        "body": body,
        "severity": severity,  # info / warning / critical
        "time": datetime.now(CST).isoformat(),
        "read": False,
    })


def render_bell_icon():
    """Render notification bell in top nav area."""
    count = _get_unread_count()
    badge = f'<span style="background:#E53935;color:#fff;border-radius:50%;padding:2px 6px;font-size:12px;font-weight:600;margin-left:4px;">{count}</span>' if count > 0 else ""

    return f'🔔{badge}'


def render_notification_panel():
    """Render the notification dropdown/panel."""
    notifs = st.session_state.get("notifications", [])

    if not notifs:
        st.caption("暂无通知")
        return

    for i, n in enumerate(notifs[:10]):
        severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(n.get("severity"), "⚪")
        type_label = {"alert": "预警", "briefing": "晨报", "system": "系统"}.get(n.get("type"), "通知")
        read_style = "opacity:0.6;" if n.get("read") else ""

        st.markdown(f"""
<div class="card" style="{read_style}padding:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:14px;font-weight:600;color:#E8EAED;">{severity_icon} {n.get('title', '')}</span>
        <span style="font-size:12px;font-weight:500;color:#5F6368;">{type_label} · {n.get('time', '')[:16]}</span>
    </div>
    <div style="font-size:14px;color:#9AA0A6;margin-top:6px;">{n.get('body', '')[:120]}</div>
</div>""", unsafe_allow_html=True)

        # Mark as read
        if not n.get("read"):
            n["read"] = True


def inject_alerts_to_chat(alerts: list):
    """Inject alert notifications into the AI Expert chat."""
    if not alerts or "expert_chat" not in st.session_state:
        return

    for alert in alerts:
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(alert.severity, "⚪")
        msg = (
            f"{severity_icon} **预警: {alert.name}**\n\n"
            f"{alert.detail}\n"
        )
        if alert.ai_comment:
            msg += f"\n🤖 _{alert.ai_comment}_"
        if alert.action_hint:
            msg += f"\n\n👉 建议: **{alert.action_hint}**"

        st.session_state["expert_chat"].append({"role": "assistant", "content": msg})
        add_notification("alert", f"{alert.name} {alert.title}", alert.detail,
                         "critical" if alert.severity == "high" else "warning")


def inject_briefing_to_chat(briefing: dict):
    """Inject morning briefing summary into AI Expert chat."""
    if not briefing or "expert_chat" not in st.session_state:
        return

    ms = briefing.get("market_sentiment", {})
    score = ms.get("score", 50)
    label = ms.get("label", "Neutral")
    emoji = "📈" if label == "Bullish" else "📉" if label == "Bearish" else "➡️"

    must_reads = briefing.get("must_reads", [])
    reads_text = ""
    for i, mr in enumerate(must_reads[:3], 1):
        reads_text += f"\n{i}. **{mr.get('title', '')}** — _{mr.get('summary', '')}_"

    one_liner = briefing.get("one_liner", "")

    msg = (
        f"📊 **今日投研晨报**\n\n"
        f"{emoji} 市场情绪: **{label}** ({score}/100)\n"
        f"{reads_text}\n\n"
        f"💡 _{one_liner}_\n\n"
        f"_需要我展开分析某条新闻吗？_"
    )

    st.session_state["expert_chat"].append({"role": "assistant", "content": msg})
    add_notification("briefing", f"投研晨报 · {label} {score}", one_liner, "info")
