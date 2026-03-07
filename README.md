# PFA — Personal Finance Agent

AI-powered investment research assistant for fund managers and stock traders. Multi-agent architecture (Scout/Analyst/Auditor/Secretary) with portfolio-aware news, deep analysis, and cross-model fact-checking.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize (creates data/, config/, sample portfolio)
python3 scripts/init_pfa_env.py

# 3. Run backend + frontend
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev
```

Open http://localhost:3000

## UI

- **Next.js + FastAPI**: `frontend` + `backend` (single maintained UI)

## Environment

| Variable | Required for |
|----------|--------------|
| `DASHSCOPE_API_KEY` | AI chat, analysis, OCR |
| `OPENAI_API_KEY` | Auditor (optional) |

See [AGENTS.md](AGENTS.md) for full documentation.
