"""
主题工具 — Stake 设计系统 Design Tokens

供 app_dash 与 app 共用。完全对齐 Stake.com 交易平台风格。
"""

import base64
from pathlib import Path

_LOGO_PATH = Path(__file__).resolve().parent.parent / "app" / "static" / "logo.png"


def logo_data_uri() -> str:
    """乌龟 Logo（PNG），圆形。用于顶栏、AI 头像、登录页等。"""
    if _LOGO_PATH.exists():
        with open(_LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    # Fallback：内联 SVG（Stake 冷色调）
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48' fill='none'>"
        "<path d='M10 26 C10 14 24 8 38 26 L38 30 L10 30 Z' stroke='#00e701' stroke-width='1.4' stroke-linejoin='round'/>"
        "<path d='M24 12 L30 16 L30 24 L24 28 L18 24 L18 16 Z' stroke='#00e701' stroke-width='1' stroke-linejoin='round'/>"
        "<ellipse cx='6' cy='26' rx='4' ry='3' stroke='#00e701' stroke-width='1.4'/>"
        "<circle cx='5' cy='25' r='0.8' fill='#00e701'/>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# Stake Design System — 精致交易终端风格
COLORS = {
    "brand": "#213743",           # Stake Blue (AI 气泡背景)
    "accent": "#00e701",          # Stake 绿
    "bg": "#0f212e",              # 全局背景
    "bg2": "#1a2c38",             # 卡片/容器
    "bg3": "#2f4553",             # 悬停/激活/输入框
    "border": "transparent",
    "text": "#ffffff",            # 主文字
    "text2": "#b1bad3",           # 次要说明（现价、成本等）
    "text3": "#5F6368",
    "up": "#00e701",              # 涨
    "down": "#ff4e33",            # 跌
    "brand_bg": "rgba(0, 231, 1, 0.08)",
}
