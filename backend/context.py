"""
请求级 user_id 与本地模式上下文 — 供 portfolio_store、chat_store 等读取

API 路由通过 Depends 设置后，深层调用的 load_portfolio/save_portfolio 可读取。
当请求头带 X-PFA-Local-Mode: 1 时，视为本地模式，使用本地 JSON/SQLite 存储。
"""

from contextvars import ContextVar

current_user_id: ContextVar[str] = ContextVar("current_user_id", default="admin")
force_local_storage: ContextVar[bool] = ContextVar("force_local_storage", default=False)


def get_current_user_id() -> str:
    return current_user_id.get()


def get_force_local_storage() -> bool:
    return force_local_storage.get()
