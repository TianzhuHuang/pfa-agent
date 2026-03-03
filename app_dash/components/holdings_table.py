"""Holdings table component — Stake 风格，无边框、交替背景"""

import dash.html as html
from html import escape

from pfa.theme_utils import COLORS


def holdings_table(by_account: dict, ccy_symbol: str = "¥", ccy_factor: float = 1.0) -> html.Div:
    """Render holdings by account. Border-none, alternating row bg, Stake palette."""
    sections = []
    for acct_name, acct_data in by_account.items():
        apnl = acct_data.get("pnl", 0)
        ac = COLORS["up"] if apnl >= 0 else COLORS["down"]
        ps = "+" if apnl >= 0 else ""
        value = acct_data.get("value", 0) * ccy_factor

        rows = []
        for idx, h in enumerate(acct_data.get("holdings", [])):
            pnl = h.get("pnl_cny", 0)
            pct = h.get("pnl_pct", 0)
            pc = COLORS["up"] if pnl >= 0 else COLORS["down"]
            ps2 = "+" if pnl >= 0 else ""
            val_cny = h.get("value_cny", 0) * ccy_factor
            pnl_display = pnl * ccy_factor
            row_bg = "rgba(26, 44, 56, 0.4)" if idx % 2 == 1 else "transparent"
            rows.append(
                html.Tr(
                    style={"background": row_bg},
                    children=[
                        html.Td(
                            html.Span(
                                h.get("symbol", ""),
                                className="symbol-tag",
                                style={"display": "inline-block", "padding": "4px 10px", "background": "rgba(0, 231, 1, 0.12)", "borderRadius": "6px", "fontWeight": 600, "fontSize": "13px", "color": COLORS["accent"]},
                            ),
                            style={"padding": "16px 14px"},
                        ),
                        html.Td(h.get("name", ""), style={"color": "#ffffff", "padding": "16px 14px"}),
                        html.Td(str(h.get("current_price", "—")), style={"textAlign": "right", "color": "#ffffff", "padding": "16px 14px"}),
                        html.Td(str(h.get("cost_price", "—")), style={"textAlign": "right", "color": "#b1bad3", "padding": "16px 14px"}),
                        html.Td(str(h.get("quantity", "—")), style={"textAlign": "right", "color": "#ffffff", "padding": "16px 14px"}),
                        html.Td(
                            f"{ccy_symbol}{val_cny:,.0f}",
                            style={"textAlign": "right", "color": "#ffffff", "fontWeight": 600, "padding": "16px 14px"},
                        ),
                        html.Td(
                            f"{ps2}{ccy_symbol}{pnl_display:,.0f}",
                            style={"textAlign": "right", "color": pc, "fontWeight": 600, "padding": "16px 14px"},
                        ),
                        html.Td(f"{ps2}{pct:.1f}%", style={"textAlign": "right", "color": pc, "padding": "16px 14px"}),
                    ],
                )
            )

        sections.append(
            html.Div(
                className="stake-account-section",
                style={"marginBottom": "24px"},
                children=[
                    html.Div(
                        style={
                            "fontWeight": 600,
                            "color": "#ffffff",
                            "marginBottom": "12px",
                            "fontSize": "14px",
                        },
                        children=f"{acct_name} · {ccy_symbol}{value:,.0f} · {ps}{ccy_symbol}{apnl * ccy_factor:,.0f}",
                    ),
                    html.Table(
                        className="stake-holdings-table",
                        style={"width": "100%", "borderCollapse": "collapse", "fontSize": "13px"},
                        children=[
                            html.Thead(
                                html.Tr(
                                    children=[
                                        html.Th("代码", style={"textAlign": "left", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("名称", style={"textAlign": "left", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("现价", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("成本", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("数量", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("市值", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("盈亏", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                        html.Th("涨跌%", style={"textAlign": "right", "padding": "14px", "color": "#b1bad3", "fontWeight": 600, "background": "transparent"}),
                                    ],
                                )
                            ),
                            html.Tbody(rows),
                        ],
                    ),
                ],
            )
        )
    return html.Div(children=sections)
