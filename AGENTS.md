# Frank AI OS — Agent Instructions
# Davvero Gelato · Multi-Agent Corporate Operating System

This file provides context for AI agents (Claude Flow, Codex, etc.) working on the Frank AI OS project.

---

## 🏗️ Project Architecture

**82 Python files** — multi-agent AI system for Davvero Gelato franchise network.

### Entry Points
- `main.py` — FastAPI app (production, port 8000)
- `main_cli.py` — CLI interactive mode (development)
- `frank_master.py` — Core orchestrator (FrankMaster class)

### Key Directories
```
frank-ai-os/
├── core/           # BaseAgent, Router, Memory, Executor
├── sectors/        # 10 sync wrappers for CLI (finance, operations, marketing, ...)
├── integrations/   # Email, WhatsApp, ERP, Social, Sheets, CRM
├── tasks/          # TaskManager (5W2H format)
├── utils/          # helpers (format_brl, calc_cmv_pct, etc.)
├── scheduler/      # APScheduler cron jobs
├── worker/         # RabbitMQ consumer
└── nginx/          # Reverse proxy config
```

### Agent Pattern (ALL agents follow this)
```python
class MyAgent(BaseAgent):
    SYSTEM_PROMPT = "..."   # domain-specific, cached with ephemeral
    async def analyze(self, question: str, user: str = "CEO") -> str:
        data = await self.db_fetch("SELECT ...")   # always fetch real data first
        context = self.format_db_data(data, "title")
        return await self.call_claude(question, extra_system=context)
```

### Response Format (10 blocks — enforced)
Every agent response MUST follow:
1. 🎯 DIAGNÓSTICO
2. 📊 DADOS
3. ⚠️ ALERTAS
4. 🔍 ANÁLISE
5. 📋 OPÇÕES
6. ✅ RECOMENDAÇÃO
7. 🚫 RISCOS
8. 📅 PRAZO
9. 🏆 RESULTADO ESPERADO
10. ⚖️ DECISÃO

---

## 📐 CEO Hard Rules (NEVER violate)

| Rule | Limit |
|------|-------|
| CMV | max 30% |
| Payback | max 30 months |
| ROI 24m | min 1.5x |
| Rent/Revenue | max 12% |
| EBITDA | min 10% |
| Gross Margin | min 68% |

---

## 🤖 Models Used

- `claude-opus-4-5` — FrankMaster + Directors
- `claude-sonnet-4-5` — Sub-agents
- `claude-haiku-4-5` — Router (keyword classification)

---

## 🗄️ Database (PostgreSQL 16)

Key tables: `units`, `franchisees`, `financial_monthly`, `daily_kpis`, `suppliers`,
`quality_audits`, `b2b_leads`, `frank_tasks`, `frank_lessons`, `alerts`, `inventory`

Key views: `vw_network_dre_current`, `vw_units_cmv_ranking`, `vw_executive_dashboard`, `vw_leads_funnel`

Key functions: `fn_unit_payback()`, `fn_unit_roi_24m()`, `fn_check_cmv_alerts()`

---

## ⚡ Concurrency Rules for AI Agents

- ALWAYS batch independent tool calls in a single message
- DB queries BEFORE calling Claude (never hallucinate data)
- Use `asyncio.gather()` for parallel agent execution
- Redis cache check before DB query (TTL: 300s KPIs, 3600s sessions)

---

## 🐇 RabbitMQ Queues

- `frank_tasks` — general async tasks (priority 0-10, DLQ enabled)
- `frank_alerts` — operational alerts (TTL 1h)
- `frank_reports` — scheduled reports (TTL 24h)

---

## 🚀 Running the System

```bash
# Full stack (Docker)
docker compose up -d

# CLI development
python main_cli.py

# Tests
python -c "from frank_master import FrankMaster; print('OK')"
```

---

## 📌 Coding Conventions

- All async (`async/await`) — no sync blocking in FastAPI context
- `asyncpg` for PostgreSQL (not SQLAlchemy)
- `redis.asyncio` for cache
- Pydantic v2 for request/response models
- f-strings for formatting, never % or .format()
- Type hints everywhere
- Portuguese for business logic strings, English for code
