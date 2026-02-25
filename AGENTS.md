# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

PFA (Personal Finance Agent) is an AI-powered information noise-reduction tool for fund managers and stock traders. It filters news/data channels based on the user's portfolio holdings. Currently in **Phase 1** (schemas, docs, and validation tooling only — no running backend or frontend services).

### Running the project

- **Python 3.12+** is required. Dependencies are in `requirements.txt` (currently only `jsonschema`).
- The only runnable code is `scripts/validate_portfolio.py`, which validates portfolio JSON against `config/user-profile.schema.json`.
  - With file: `python3 scripts/validate_portfolio.py config/sample-portfolio.json`
  - From stdin: `echo '{"version":"1.0"}' | python3 scripts/validate_portfolio.py`
- There are no backend servers, frontend apps, Docker containers, or databases at this stage.

### Linting and testing

- No dedicated linter or test framework is configured yet. Use `python3 -m py_compile <file>` for syntax checks.
- No automated test suite exists; validate correctness by running the validation script against `config/sample-portfolio.json`.

### Security constraints (from `.cursorrules`)

- Never store plaintext broker credentials in cloud/logs.
- Agent has **read-only** permissions — no trading operations.
- Do not print full portfolio details in logs; use masked summaries only.

### Key files

| File | Purpose |
|---|---|
| `config/user-profile.schema.json` | JSON Schema for user profiles & holdings |
| `config/sample-portfolio.json` | Sample valid portfolio for testing |
| `scripts/validate_portfolio.py` | CLI tool to validate portfolio JSON |
| `docs/product-scope.md` | Product goals and MVP definition |
| `docs/security-architecture.md` | Security rules (read-only, data masking) |
| `docs/data-sources.md` | Data source specifications |
| `.cursorrules` | Mandatory coding rules for this project |
