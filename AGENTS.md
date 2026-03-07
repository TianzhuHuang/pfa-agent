# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered investment research assistant for fund managers and stock traders. Multi-agent architecture (Scout/Analyst/Auditor/Secretary) with 7+ data sources, Telegram push, and real-time portfolio valuation.

**Current phase**: Next.js + FastAPI UI is the maintained path; Phase 4 (Supabase multi-user) in design.

### Running the project

- **Python 3.12+** required. Install: `pip install -r requirements.txt`
- **本地与云端差异**：云端 Cursor 在固定根目录、依赖齐全的环境下跑；本地 checkout 后若未装依赖、未建 `data/`/`config` 或未在根目录启动，容易出现 ImportError 或找不到配置。建议在项目根目录执行一次：`python3 scripts/init_pfa_env.py`，再运行下面命令。详见 `docs/local-environment.md`。
- **PFA v2（Next.js + FastAPI）**: 分支 `pfa-v2-dev`。后端 `uvicorn backend.main:app --port 8000`，前端 `cd frontend && npm run dev` → http://localhost:3000。详见 `docs/pfa-v2-quickstart.md`。
- **Scheduler (auto briefing + alerts)**: `python -m pfa.scheduler --run-now`
- **Alert scan only**: `python -c "from pfa.alert_engine import run_alert_scan; run_alert_scan()"`
- Portfolio validation: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- News fetching: `python3 scripts/fetch_holding_news.py` (East Money API)
- RSS fetching: `python3 scripts/fetch_rss.py` (from `channels.rss_urls` in portfolio)
- Deep analysis: `python3 scripts/fetch_holding_news.py --analyze` (requires `DASHSCOPE_API_KEY`)
- **Control Center**: Next.js pages: 持仓大盘 / 综合早报 / 分析中心 / 数据源配置
- Data stored in `data/store/` (unified layer) and `data/raw/` (legacy).

### Key modules

| Module | Purpose |
|---|---|
| `agents/scout_agent.py` | Multi-source fetcher (East Money + 华尔街见闻 + RSS + RSSHub) |
| `agents/analyst_agent.py` | Structured briefing output (JSON: sentiment + must_reads + portfolio_moves) |
| `agents/auditor_agent.py` | Cross-model fact-checking (OpenAI → qwen-max fallback) |
| `agents/secretary_agent.py` | Orchestrator + portfolio CRUD + memo management |
| `pfa/realtime_quote.py` | Sina Finance real-time quotes (~1.8s for all holdings) |
| `pfa/alert_engine.py` | Price/keyword triggers + AI analysis + memo cross-check |
| `pfa/telegram_push.py` | Formatted briefing + alert push to Telegram |
| `pfa/scheduler.py` | APScheduler cron (default: 8:00 AM CST daily) |
| `pfa/stock_search.py` | East Money autocomplete API |
| `pfa/screenshot_ocr.py` | Qwen-VL multimodal portfolio screenshot recognition |
| `pfa/ai_portfolio_assistant.py` | Natural language portfolio CRUD (Qwen) |
| `pfa/portfolio_valuation.py` | FX rates + real-time valuation + P&L calculation |
| `pfa/data/store.py` | Unified data layer (user_id param for multi-tenant) |
| `backend/database/` | SQLite + SQLAlchemy（对话持久化，替代 JSON） |
| `backend/services/chat_store.py` | 对话存储（DB 优先，JSON 回退） |
| `app/theme.py` | Dark/light theme system + card components |
| `chrome-extension/` | Xueqiu WAF bypass Chrome extension |

### Data sources (7 active)

| Source | Type | Notes |
|---|---|---|
| 东方财富 | API (per-stock) | No key needed |
| 华尔街见闻 | API (macro) | No key needed |
| 财联社电报 | RSSHub | Needs self-hosted RSSHub (Docker) |
| 格隆汇快讯 | RSSHub | Same |
| 金十快讯 | RSSHub | Same |
| 36kr | RSS | Direct |
| FT中文网 | RSS | Direct |

### Environment variables

| Variable | Required for | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | Analyst + Auditor + OCR + AI assistant | 通义千问 API (qwen-plus, qwen-max, qwen-vl-plus) |
| `OPENAI_API_KEY` | Auditor (preferred) | Cross-model fact-checking. Auto-fallback to qwen-max |
| `TELEGRAM_BOT_TOKEN` | Telegram push | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Telegram push | Auto-discovered via `python -m pfa.telegram_push --discover` |
| `SUPABASE_URL` | Phase 4 (multi-user) | Supabase project URL |
| `SUPABASE_ANON_KEY` | Phase 4 (multi-user) | Supabase anon/public key |

### Gotchas

- Real-time quotes use Sina Finance API (~1.8s). Playwright/Xueqiu is fallback only.
- RSSHub sources (财联社/格隆汇/金十) need `docker run -d -p 1200:1200 diygod/rsshub`.
- Xueqiu user pages require Chrome extension (WAF blocks headless browsers).
- A-share color convention: red = bullish (涨), green = bearish (跌).
- `data/users/{user_id}/store/` is the new storage path; legacy `data/store/` auto-migrated.
- Default theme is light (white). Toggle in sidebar.

### Phase 4 plan

See `docs/phase4-plan.md` for Supabase multi-user architecture design (DB schema, RLS, migration path).
