# PFA — Personal Finance Agent

AI-powered investment research assistant for fund managers and stock traders. Multi-agent architecture (Scout/Analyst/Auditor/Secretary) with portfolio-aware news, deep analysis, and cross-model fact-checking.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize (creates data/, config/, sample portfolio)
python3 scripts/init_pfa_env.py

# 3. Run Dash UI
python3 app_dash/app.py
```

Open http://127.0.0.1:8050

## UI

- **Dash** (recommended): `python3 app_dash/app.py` — Traditional AI Chat, holdings, briefing, analysis
- **Streamlit** (legacy): `streamlit run app/pfa_dashboard.py --server.port 8501`

## Environment

| Variable | Required for |
|----------|--------------|
| `DASHSCOPE_API_KEY` | AI chat, analysis, OCR |
| `OPENAI_API_KEY` | Auditor (optional) |

See [AGENTS.md](AGENTS.md) for full documentation.
