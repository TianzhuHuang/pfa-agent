"""
数据库会话与初始化
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.database.models import Base

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "pfa.db"

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()


def init_db():
    """创建所有表，并迁移 chat_messages、holdings 列（若不存在）。"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_chat_messages(engine)
    _migrate_holdings_ocr(engine)
    _migrate_accounts_balance(engine)


def _migrate_accounts_balance(engine):
    """为 accounts 添加 balance 列。"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN balance REAL"))
            conn.commit()
    except Exception:
        pass  # 列已存在或其它错误，忽略


def _migrate_holdings_ocr(engine):
    """为 holdings 添加 ocr_confirmed、price_deviation_warn 列。"""
    from sqlalchemy import text
    for col in ("ocr_confirmed", "price_deviation_warn"):
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE holdings ADD COLUMN {col} BOOLEAN"))
                conn.commit()
        except Exception:
            pass  # 列已存在或其它错误，忽略


def _migrate_chat_messages(engine):
    """为 chat_messages 添加 symbol、session_id 列（兼容已有数据库）。"""
    from sqlalchemy import text
    for col in ("symbol", "session_id"):
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE chat_messages ADD COLUMN {col} VARCHAR(64)"))
                conn.commit()
        except Exception:
            pass  # 列已存在或其它错误，忽略
