"""
PFA Agent 通信协议

所有 Agent 之间通过 AgentMessage (JSON) 交换信息，
每个模块可独立测试。
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

CST = timezone(timedelta(hours=8))


@dataclass
class AgentMessage:
    """Agent 间通信的标准消息格式。"""

    msg_id: str = ""
    timestamp: str = ""
    sender: str = ""           # scout / analyst / auditor / secretary
    receiver: str = ""         # 目标 agent 或 "broadcast"
    msg_type: str = ""         # request / response / event
    action: str = ""           # fetch_news / analyze / audit / render ...
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"         # ok / error
    error: str = ""

    def __post_init__(self):
        if not self.msg_id:
            self.msg_id = uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(CST).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentMessage":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def make_request(
    sender: str, receiver: str, action: str, **payload
) -> AgentMessage:
    return AgentMessage(
        sender=sender, receiver=receiver,
        msg_type="request", action=action, payload=payload,
    )


def make_response(
    request: AgentMessage, sender: str, **payload
) -> AgentMessage:
    return AgentMessage(
        sender=sender, receiver=request.sender,
        msg_type="response", action=request.action,
        payload=payload,
    )


def make_error(
    request: AgentMessage, sender: str, error: str
) -> AgentMessage:
    return AgentMessage(
        sender=sender, receiver=request.sender,
        msg_type="response", action=request.action,
        status="error", error=error,
    )
