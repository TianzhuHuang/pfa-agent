"""
HTTP 请求出口 — 支持经 Cloudflare Workers 代理（阿里云等机房环境）

当设置环境变量 PFA_PROXY_BASE 时，对易被机房拦截的请求（Yahoo/东财/新浪/Binance/CoinGecko）
改为请求 Worker：GET {PFA_PROXY_BASE}?url={encoded_target_url}，由 Worker 转发并返回目标响应体。
未设置时与 requests.get 行为一致（直连）。

如果 workers.dev 持续报错（如 Network unreachable），请在 Cloudflare 后台将 Worker 绑定到
自定义域名（如 api.yourdomain.com），并将该域名填入 PFA_PROXY_BASE。
"""

from __future__ import annotations

import logging
import os
from urllib.parse import quote, urlencode

import requests

_log = logging.getLogger("pfa.proxy_fetch")

DEFAULT_TIMEOUT = 10


def _proxy_base() -> str | None:
    v = os.environ.get("PFA_PROXY_BASE") or os.environ.get("pfa_proxy_base")
    if not v or not str(v).strip():
        return None
    return str(v).strip().rstrip("/")


def get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> requests.Response:
    """
    发起 GET 请求。若 PFA_PROXY_BASE 已设置，则请求通过 Worker 代理转发至 url；
    否则直连。返回 requests.Response，调用方照常 .json() / .text / .raise_for_status()。
    """
    base = _proxy_base()
    if params:
        full_url = url + ("&" if "?" in url else "?") + urlencode(params)
    else:
        full_url = url

    if base:
        proxy_url = f"{base}?url={quote(full_url)}"
        _log.debug("proxy_fetch: %s -> %s", full_url[:80], proxy_url[:80])
        resp = requests.get(proxy_url, headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        return resp

    return requests.get(full_url, headers=headers or {}, timeout=timeout)


def use_proxy() -> bool:
    """是否配置了代理（便于上层决定是否走 proxy_fetch）。"""
    return _proxy_base() is not None
