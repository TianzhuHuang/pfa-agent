# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered information noise-reduction tool for fund managers and stock traders. It uses a **multi-agent architecture** (Scout/Analyst/Auditor/Secretary) for portfolio-aware news fetching, deep analysis, and cross-model fact-checking.

### Running the project

- **Python 3.12+** is required. Dependencies are in `requirements.txt`.
- Portfolio validation: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- News fetching: `python3 scripts/fetch_holding_news.py` (East Money API)
- RSS fetching: `python3 scripts/fetch_rss.py` (from `channels.rss_urls` in portfolio)
- Deep analysis: `python3 scripts/fetch_holding_news.py --analyze` (requires `DASHSCOPE_API_KEY`)
- **Control Center**: `streamlit run app/pfa_dashboard.py --server.port 8501`
  - 持仓管理: 手动添加 / CSV·JSON 批量导入 / 表格编辑
  - 数据源配置: RSS / Twitter / URL / 雪球 动态管理 → `config/data-sources.json`
  - 执行分析: 单标的 Scout 抓取 / 全流水线 Scout→Analyst→Auditor
  - 分析存档: 按日期回溯历史分析
- Data stored in `data/store/` (unified layer) and `data/raw/` (legacy).

### Linting and testing

- No dedicated linter or test framework is configured yet. Use `python3 -m py_compile <file>` for syntax checks.
- Validate portfolio: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- Test fetch pipeline: `python3 scripts/fetch_holding_news.py --hours 24` (should produce output in `data/raw/`).
- Test full pipeline (fetch + analysis): `python3 scripts/fetch_holding_news.py --hours 72 --analyze`

### Gotchas

- The East Money search API returns JSONP; the script strips the wrapper automatically.
- DashScope API uses OpenAI-compatible format at `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`; no `openai` SDK needed, `requests` handles it directly.
- News for some holdings (e.g. 片仔癀) may return 0 results in short time windows; this is normal if no recent news exists. Widen `--hours` to verify.

### Security constraints (from `.cursorrules`)

- Never store plaintext broker credentials in cloud/logs.
- Agent has **read-only** permissions — no trading operations.
- Do not print full portfolio details in logs; use masked summaries only.

### Key files

| File | Purpose |
|---|---|
| `config/user-profile.schema.json` | JSON Schema for user profiles & holdings |
| `config/my-portfolio.json` | Active portfolio (3 holdings: 茅台, 片仔癀, 中海油) |
| `config/sample-portfolio.json` | Sample valid portfolio for testing |
| `scripts/validate_portfolio.py` | CLI tool to validate portfolio JSON |
| `scripts/fetch_holding_news.py` | Fetch news for portfolio holdings (East Money API) |
| `scripts/fetch_rss.py` | Fetch and match RSS feeds to holdings |
| `pfa/data/store.py` | Unified data layer (FeedItem / AnalysisRecord) |
| `agents/protocol.py` | Agent JSON communication protocol (AgentMessage) |
| `agents/scout_agent.py` | Data Scout — wraps East Money fetcher |
| `agents/analyst_agent.py` | Analyst — Qwen qwen-plus deep analysis |
| `agents/auditor_agent.py` | Auditor — cross-model fact-checking (OpenAI or qwen-max) |
| `agents/secretary_agent.py` | Secretary — orchestrates Scout→Analyst→Auditor pipeline |
| `app/pfa_dashboard.py` | Streamlit dashboard entry point |
| `docs/phase3-design.md` | Phase 3 knowledge base & Skill design |
| `docs/product-scope.md` | Product goals and MVP definition |
| `docs/security-architecture.md` | Security rules (read-only, data masking) |
| `docs/data-sources.md` | Data source specifications |
| `.cursorrules` | Mandatory coding rules for this project |

### Environment variables

| Variable | Required for | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | Analyst + Auditor fallback | 通义千问 API key (Analyst uses qwen-plus, Auditor fallback uses qwen-max) |
| `OPENAI_API_KEY` | Auditor (preferred) | OpenAI API key for cross-model fact-checking. Auto-fallback to qwen-max if key is invalid or missing |
