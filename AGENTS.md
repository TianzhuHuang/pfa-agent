# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered information noise-reduction tool for fund managers and stock traders. It filters news/data channels based on the user's portfolio holdings. Currently in **Phase 1** (schemas, docs, and validation tooling only — no running backend or frontend services).

### Running the project

- **Python 3.12+** is required. Dependencies are in `requirements.txt`.
- Portfolio validation: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- News fetching: `python3 scripts/fetch_holding_news.py` (fetches news for holdings in `config/my-portfolio.json`)
  - With Qwen analysis: `python3 scripts/fetch_holding_news.py --analyze` (requires `DASHSCOPE_API_KEY`)
  - Custom time window: `python3 scripts/fetch_holding_news.py --hours 48`
- Raw data is stored in `data/raw/` (gitignored except `.gitkeep`).
- There are no backend servers, frontend apps, Docker containers, or databases.

### Linting and testing

- No dedicated linter or test framework is configured yet. Use `python3 -m py_compile <file>` for syntax checks.
- Validate portfolio: `python3 scripts/validate_portfolio.py config/my-portfolio.json`
- Test fetch pipeline: `python3 scripts/fetch_holding_news.py --hours 24` (should produce output in `data/raw/`).

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
| `docs/product-scope.md` | Product goals and MVP definition |
| `docs/security-architecture.md` | Security rules (read-only, data masking) |
| `docs/data-sources.md` | Data source specifications |
| `.cursorrules` | Mandatory coding rules for this project |

### Environment variables

| Variable | Required for | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | `--analyze` flag | 通义千问 (DashScope) API key for deep news analysis |
