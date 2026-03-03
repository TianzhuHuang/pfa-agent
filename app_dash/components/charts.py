"""Charts — Plotly 图表，Stake 绿 + 深灰蓝"""

import plotly.graph_objects as go
from typing import Dict, List

# Stake：绿 #00e701 + 深灰蓝 #2f4553
CHART_COLORS = {
    "paper": "#1a2c38",
    "plot": "rgba(0,0,0,0)",
    "text": "#b1bad3",
    "up": "#00e701",
    "down": "#ff4e33",
    "palette": ["#00e701", "#2f4553", "#3d5a6c", "#4a6b7c", "#5a7a8a"],
}


def allocation_pie(holdings_data: List[Dict], total_value: float, ccy_symbol: str = "¥") -> go.Figure:
    """仓位占比饼图 — 中心白色大字，环形 Stake 绿 + #2f4553"""
    labels, values = [], []
    for h in sorted(holdings_data, key=lambda x: x.get("value_cny", 0), reverse=True):
        name = h.get("name", h.get("symbol", "?"))
        val = h.get("value_cny", 0)
        if val <= 0:
            continue
        pct = val / total_value * 100 if total_value > 0 else 0
        labels.append(f"{name} {pct:.1f}%")
        values.append(val)

    if not values:
        return go.Figure()

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(
                    colors=CHART_COLORS["palette"][: len(labels)],
                    line=dict(color="#0f212e", width=2),
                ),
                textinfo="none",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_COLORS["paper"],
        plot_bgcolor=CHART_COLORS["plot"],
        font=dict(color=CHART_COLORS["text"], size=12),
        margin=dict(l=0, r=0, t=30, b=0),
        height=260,
        showlegend=True,
        legend=dict(
            font=dict(size=11),
            orientation="v",
            y=0.5,
            bgcolor="rgba(0,0,0,0)",
        ),
        annotations=[
            dict(
                text=f"<b>{ccy_symbol}{total_value/10000:,.0f}万</b>",
                x=0.5,
                y=0.5,
                font_size=20,
                font_color="#ffffff",
                showarrow=False,
            )
        ],
    )
    return fig
