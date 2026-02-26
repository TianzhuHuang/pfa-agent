# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered investment research assistant for fund managers and stock traders. Multi-agent architecture (Scout/Analyst/Auditor/Secretary) with 7+ data sources, Telegram push, and real-time portfolio valuation.

**Current phase**: Phase 3 complete, Phase 4 (Supabase multi-user) in design.

### Running the project

- **Python 3.12+** required. Install: `pip install -r requirements.txt`
- **Streamlit UI**: `streamlit run app/pfa_dashboard.py --server.port 8501`
- **Scheduler (auto briefing + alerts)**: `python -m pfa.scheduler --run-now`
- **Alert scan only**: `python -c "from pfa.alert_engine import run_alert_scan; run_alert_scan()"`

### Pages (5)

| Page | URL path | Description |
|---|---|---|
| 持仓大盘 | `/持仓管理` | Global Net Worth + multi-account + Ask PFA AI chat + memo timeline |
| 综合早报 | `/综合早报` | ClawFeed-style: sentiment score + must-reads + portfolio moves |
| 分析中心 | `/分析中心` | Scout→Analyst→Auditor console + history archive (visual render) |
| 个股深度 | `/个股深度` | 3-column: fundamentals+P&L / news feed / Ask Agent chat |
| 数据源配置 | `/数据源配置` | RSS/API sources + health check test buttons |

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
