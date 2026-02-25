# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered information noise-reduction tool for fund managers and stock traders. It filters news/data channels based on the user's portfolio holdings. Phase 2 data layer is active: news fetching (East Money) + deep analysis (通义千问 qwen-plus via DashScope).

### Running the project

- **Python 3.12+** is required. Dependencies are in `requirements.txt`.
- Portfolio validation: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- News fetching: `python3 scripts/fetch_holding_news.py` (East Money API)
- RSS fetching: `python3 scripts/fetch_rss.py` (from `channels.rss_urls` in portfolio)
- Deep analysis: `python3 scripts/fetch_holding_news.py --analyze` (requires `DASHSCOPE_API_KEY`)
- Streamlit dashboard: `streamlit run app/pfa_dashboard.py --server.port 8501`
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
| `app/pfa_dashboard.py` | Streamlit dashboard entry point |
| `docs/phase3-design.md` | Phase 3 knowledge base & Skill design |
| `docs/product-scope.md` | Product goals and MVP definition |
| `docs/security-architecture.md` | Security rules (read-only, data masking) |
| `docs/data-sources.md` | Data source specifications |
| `.cursorrules` | Mandatory coding rules for this project |

### Environment variables

| Variable | Required for | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | `--analyze` flag | 通义千问 (DashScope) API key for deep news analysis |
