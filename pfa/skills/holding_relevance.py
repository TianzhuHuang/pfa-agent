from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RelevanceHit:
    symbol: str
    name: str = ""
    reason: str = ""
    score: int = 0  # 0-100


def score_relevance(
    *,
    text: str,
    holdings: List[dict],
) -> List[RelevanceHit]:
    """Very small local heuristic relevance scorer.

    This is a placeholder Skill: it provides deterministic behavior without requiring an LLM.
    """
    t = (text or "").lower()
    out: List[RelevanceHit] = []
    for h in holdings:
        sym = str(h.get("symbol", "") or "").strip()
        name = str(h.get("name", "") or "").strip()
        if not sym and not name:
            continue
        score = 0
        reason_parts: List[str] = []
        if sym and sym.lower() in t:
            score += 70
            reason_parts.append("命中代码")
        if name and name.lower() in t:
            score += 50
            reason_parts.append("命中名称")
        if score > 0:
            out.append(RelevanceHit(symbol=sym or name, name=name, score=min(score, 100), reason="，".join(reason_parts)))
    out.sort(key=lambda x: x.score, reverse=True)
    return out[:5]

