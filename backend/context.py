"""
请求级 user_id 上下文 — 供 portfolio_store、chat_store 等读取

API 路由通过 Depends 设置后，深层调用的 load_portfolio/save_portfolio 可读取。
"""

from contextvars import ContextVar

current_user_id: ContextVar[str] = ContextVar("current_user_id", default="admin")


def get_current_user_id() -> str:
    return current_user_id.get()
