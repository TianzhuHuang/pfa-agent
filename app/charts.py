"""
PFA 专业图表组件 — Plotly 暗色金融风格

所有图表遵循设计系统:
  背景: transparent / #1A1D26
  文字: #9AA0A6
  涨: #E53935 (A股红)
  跌: #43A047 (A股绿)
"""

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from typing import Dict, List

CHART_COLORS = {
    "bg": "rgba(0,0,0,0)",
    "paper": "#1A1D26",
    "grid": "#2D3139",
    "text": "#9AA0A6",
    "up": "#E53935",
    "down": "#43A047",
    "accent": "#4285F4",
    "palette": ["#4285F4", "#E53935", "#FBBC04", "#43A047", "#AB47BC",
                "#FF7043", "#26C6DA", "#9CCC65", "#EC407A", "#78909C"],
}

LAYOUT_BASE = dict(
    paper_bgcolor=CHART_COLORS["paper"],
    plot_bgcolor=CHART_COLORS["bg"],
    font=dict(family="Inter, sans-serif", color=CHART_COLORS["text"], size=12),
    margin=dict(l=0, r=0, t=30, b=0),
    height=280,
)


def render_allocation_pie(holdings_data: List[Dict], total_value: float):
    """仓位占比饼图 (Position Sizing)."""
    labels = []
    values = []
    colors = []

    for h in sorted(holdings_data, key=lambda x: x.get("value_cny", 0), reverse=True):
        name = h.get("name", h.get("symbol", "?"))
        val = h.get("value_cny", 0)
        if val <= 0:
            continue
        pct = val / total_value * 100 if total_value > 0 else 0
        labels.append(f"{name} {pct:.1f}%")
        values.append(val)

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=CHART_COLORS["palette"][:len(labels)],
                    line=dict(color="#0F1116", width=2)),
        textinfo="none",
        hovertemplate="%{label}<br>¥%{value:,.0f}<extra></extra>",
    )])

    fig.update_layout(
        **LAYOUT_BASE,
        showlegend=True,
        legend=dict(
            font=dict(size=11, color=CHART_COLORS["text"]),
            bgcolor="rgba(0,0,0,0)",
            orientation="v",
            y=0.5,
        ),
        height=260,
        annotations=[dict(
            text=f"<b>¥{total_value/10000:,.0f}万</b>",
            x=0.5, y=0.5, font_size=16, font_color="#E8EAED",
            showarrow=False,
        )],
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_market_distribution(by_market: Dict):
    """市场分布横条图."""
    markets = []
    values = []
    for mkt, data in sorted(by_market.items(), key=lambda x: x[1]["value"], reverse=True):
        label = {"A": "A 股", "HK": "港股", "US": "美股", "OTHER": "其他"}.get(mkt, mkt)
        markets.append(label)
        values.append(data["value"])

    fig = go.Figure(data=[go.Bar(
        x=values, y=markets, orientation="h",
        marker=dict(color=CHART_COLORS["palette"][:len(markets)]),
        text=[f"¥{v:,.0f}" for v in values],
        textposition="auto",
        textfont=dict(color="#E8EAED", size=12),
    )])

    fig.update_layout(
        **LAYOUT_BASE,
        height=120 + 30 * len(markets),
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False, showticklabels=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_pnl_waterfall(holdings_data: List[Dict]):
    """今日盈亏贡献瀑布图."""
    sorted_h = sorted(holdings_data, key=lambda x: x.get("today_pnl", 0), reverse=True)

    names = []
    pnls = []
    colors = []

    for h in sorted_h:
        today_pnl = h.get("today_pnl", 0)
        if today_pnl == 0:
            continue
        name = h.get("name", h.get("symbol", "?"))
        names.append(name[:4])
        pnls.append(today_pnl)
        colors.append(CHART_COLORS["up"] if today_pnl >= 0 else CHART_COLORS["down"])

    if not names:
        return

    fig = go.Figure(data=[go.Bar(
        x=names, y=pnls,
        marker=dict(color=colors),
        text=[f"{'+'if p>=0 else ''}{p:,.0f}" for p in pnls],
        textposition="outside",
        textfont=dict(size=11, color=CHART_COLORS["text"]),
    )])

    fig.update_layout(
        **LAYOUT_BASE,
        height=200,
        yaxis=dict(showgrid=True, gridcolor=CHART_COLORS["grid"],
                   zeroline=True, zerolinecolor=CHART_COLORS["grid"]),
        xaxis=dict(showgrid=False),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
