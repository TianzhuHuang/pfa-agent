"""
PFA API Schemas — 账户与持仓模型

供 API 与 secretary 复用。
"""

from pydantic import BaseModel
from typing import Optional


class AccountBase(BaseModel):
    """账户基础模型"""
    name: str
    base_currency: str = "CNY"
    broker: str = ""
    account_type: str = "股票"


class AccountCreate(AccountBase):
    """创建账户"""
    pass


class AccountUpdate(BaseModel):
    """更新账户（部分字段）"""
    name: Optional[str] = None
    base_currency: Optional[str] = None
    broker: Optional[str] = None
    account_type: Optional[str] = None


class AccountOut(AccountBase):
    """账户输出（含 id 与时间戳）"""
    id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
