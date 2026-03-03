"""
PFA 数据库模型 — ChatHistory, Account, Holding
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ChatMessage(Base):
    """对话记录：User/AI 消息，带时间戳。symbol/session_id 为 null 表示首页全局对话。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="admin", index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)  # 保留 \n\n 换行
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)  # 标的代码，null=首页
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)  # 会话 ID，同 symbol 下多会话

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Account(Base):
    """账户：名称、币种、类型。"""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="admin", index=True)
    account_id: Mapped[str] = mapped_column(String(128), unique=True)  # 业务 ID，如 "盈透"
    name: Mapped[str] = mapped_column(String(128))
    base_currency: Mapped[str] = mapped_column(String(8), default="CNY")
    broker: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    account_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    balance: Mapped[Optional[float]] = mapped_column(nullable=True, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Holding(Base):
    """持仓明细：标的、数量、成本、账户。"""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="admin", index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    market: Mapped[str] = mapped_column(String(8), default="A")
    quantity: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    account: Mapped[str] = mapped_column(String(128), default="默认")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    position_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memo_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ocr_confirmed: Mapped[Optional[bool]] = mapped_column(nullable=True)
    price_deviation_warn: Mapped[Optional[bool]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioMeta(Base):
    """组合元数据：channels, preferences。"""

    __tablename__ = "portfolio_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="admin", index=True)
    meta_key: Mapped[str] = mapped_column(String(32), index=True)  # channels | preferences
    meta_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FxRate(Base):
    """汇率表：每日更新。"""

    __tablename__ = "fx_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    currency: Mapped[str] = mapped_column(String(8), index=True)  # USD, HKD
    rate_to_cny: Mapped[float] = mapped_column(Float)  # 1 unit -> CNY
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BriefingReport(Base):
    """晨报报告：按日期持久化。"""

    __tablename__ = "briefing_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="admin", index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime, index=True)  # 报告日期（当天 00:00）
    content: Mapped[str] = mapped_column(Text)  # JSON 序列化的完整 briefing
    summary: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 一句话摘要（≤20 字）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.report_date.strftime("%Y-%m-%d") if self.report_date else None,
            "content": self.content,
            "summary": self.summary or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
