"""
PFA Backend — FastAPI

投研逻辑、持仓计算、AI Chat 的 REST/SSE 接口。
必须在项目根目录启动：uvicorn backend.main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path

# 项目根目录加入 path（与 Dash 一致，确保 pfa/agents 可导入）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 加载 .env（项目根目录）
_env = ROOT / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

_log = logging.getLogger("backend.main")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import portfolio, chat, briefing, settings_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库并同步汇率。"""
    try:
        from backend.database.session import init_db
        init_db()
    except Exception:
        pass
    try:
        from backend.services.fx_service import sync_fx_rates
        sync_fx_rates()
    except Exception:
        pass
    yield
    # shutdown if needed
    pass


app = FastAPI(title="PFA API", version="2.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """确保 500 等错误返回 JSON，便于前端解析"""
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": str(exc)},
    )

_default_cors = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000"
_site_url = os.environ.get("SITE_URL") or os.environ.get("NEXT_PUBLIC_SITE_URL")
_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    f"{_site_url},http://127.0.0.1:3000" if _site_url else _default_cors,
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _decode_supabase_jwt(token: str) -> str | None:
    """
    解析 Supabase JWT，返回 sub (user_id) 或 None。
    优先 JWKS (ES256)，失败时回退 HS256（Legacy JWT Secret 仅对旧 HS256 签发的 token 有效）。
    当前项目若已迁移至 ECC，新 token 必须通过 JWKS 验证。
    """
    supabase_url = (os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    if not supabase_url or not token:
        return None
    import jwt

    skip_aud = os.environ.get("PFA_JWT_SKIP_AUDIENCE", "").strip() == "1"
    decode_opts = {"verify_exp": True, "verify_aud": not skip_aud}

    # 1. 优先 JWKS (ES256/RS256) — 当前 Supabase 默认
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        jwks_client = jwt.PyJWKClient(jwks_url, timeout=15)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            options=decode_opts,
        )
        sub = payload.get("sub")
        return str(sub) if sub else None
    except Exception as e:
        _log.info("JWT JWKS 解析失败，尝试 HS256: %s", e)

    # 2. 回退 HS256（Legacy JWT Secret，仅对 HS256 签发的 token 有效）
    secret = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
    if secret:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                options=decode_opts,
            )
            sub = payload.get("sub")
            return str(sub) if sub else None
        except Exception as e2:
            _log.warning("JWT HS256 解析失败: %s", e2)
    return None


@app.middleware("http")
async def set_user_context(request, call_next):
    """从 Authorization 头解析 user_id 并设置到 context，供 portfolio_store 等读取。"""
    from backend.context import current_user_id

    user_id = "admin"
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:]
        decoded = _decode_supabase_jwt(token)
        if decoded:
            user_id = decoded
        else:
            _log.info("JWT 未解析出 user_id（JWKS/HS256 均失败），将使用 admin")
    elif auth:
        _log.debug("Authorization 头格式异常（非 Bearer）")

    token = current_user_id.set(user_id)
    try:
        return await call_next(request)
    finally:
        current_user_id.reset(token)

app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
# chat 路由需在 briefing 之前注册，避免 /api/analysis/{id} 等动态路由优先匹配
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(briefing.router, prefix="/api", tags=["briefing"])
app.include_router(settings_api.router, prefix="/api", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    """检查后端环境：项目路径、.env、股票搜索、OCR 依赖。用于本地排查。"""
    import os
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    env_ok = bool(os.environ.get("DASHSCOPE_API_KEY"))
    env_file = root / ".env"
    env_exists = env_file.exists()
    search_ok = False
    search_err = None
    try:
        from pfa.stock_search import search_stock
        r = search_stock("茅台", count=2)
        search_ok = len(r) > 0
    except Exception as e:
        search_err = str(e)
    return {
        "status": "ok",
        "root": str(root),
        "env_file_exists": env_exists,
        "DASHSCOPE_API_KEY_set": env_ok,
        "stock_search_ok": search_ok,
        "search_err": search_err,
    }
