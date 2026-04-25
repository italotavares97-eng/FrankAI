# Frank AI OS — Claude Code Project Guide

> Davvero Gelato · Multi-Agent Corporate AI Operating System
> Claude Flow v2.5.0 integrated

---

## ⚡ GOLDEN RULE (Claude Flow)

**1 MESSAGE = ALL OPERATIONS**

Always batch independent tool calls in a single message. Never sequence what can run in parallel.

---

## 🏗️ Architecture Summary

```
frank-ai-os/                    82 Python files
├── main.py                     FastAPI app (port 8000)
├── main_cli.py                 CEO CLI (interactive dev mode)
├── frank_master.py             FrankMaster orchestrator
├── config.py                   Models, rules, env vars
├── core/                       BaseAgent, Router, Memory, Executor
├── sectors/                    10 sync CLI wrappers
├── integrations/               Email, WhatsApp, ERP, Social, Sheets, CRM
├── scheduler/                  APScheduler (cron jobs)
├── worker/                     RabbitMQ consumer
├── nginx/                      Reverse proxy (production)
├── rabbitmq/                   Queue definitions
├── tasks/                      TaskManager (5W2H)
└── utils/                      Business logic helpers
```

**8 AI Directors** → 37 specialized agents → FrankMaster orchestrates

**Models**: Opus 4.5 (directors) | Sonnet 4.5 (agents) | Haiku 4.5 (router)

---

## 🧠 Agent Coding Pattern

```python
class MyAgent(BaseAgent):
    SYSTEM_PROMPT = "You are..."   # ephemeral cache_control applied automatically

    async def analyze(self, question: str, user: str = "CEO") -> str:
        # 1. Fetch real data from DB
        data = await self.db_fetch("SELECT ...")
        context = self.format_db_data(data, "title")
        # 2. Call Claude with context
        return await self.call_claude(question, extra_system=context)
```

**Response format** (10 blocks — always):
🎯 DIAGNÓSTICO → 📊 DADOS → ⚠️ ALERTAS → 🔍 ANÁLISE → 📋 OPÇÕES → ✅ RECOMENDAÇÃO → 🚫 RISCOS → 📅 PRAZO → 🏆 RESULTADO → ⚖️ DECISÃO

---

## 📐 CEO Hard Rules (never violate)

| Rule | Limit | Agent that enforces |
|------|-------|---------------------|
| CMV | ≤ 30% | `frank_master._ceo_validate()` |
| Payback | ≤ 30m | same |
| ROI 24m | ≥ 1.5x | same |
| Rent | ≤ 12% revenue | same |
| EBITDA | ≥ 10% | same |

---

## 🐝 Claude Flow Swarm — Frank AI OS Workflows

### Full analysis swarm
```
/frank-swarm-analyze
```
Spawns: CFO + COO + CMO agents in parallel, consolidates via FrankMaster.

### Daily KPI generation
```
/frank-daily-kpi
```
Triggers scheduler → KPI agent → email report.

### CMV audit swarm
```
/frank-cmv-audit
```
Spawns CMV agent for all 7 units simultaneously, generates alerts.

### Expansion evaluation
```
/frank-expansion-eval
```
CSO + CFO + Legal agents evaluate new unit viability.

---

## 🚀 Quick Commands

```bash
# Start full stack
docker compose up -d

# CLI mode
python main_cli.py

# Check API health
curl http://localhost:8000/health

# Run seeds
docker compose exec postgres psql -U frank -d davvero -f /docker-entrypoint-initdb.d/02_seeds.sql

# Logs
docker compose logs -f frank frank_worker
```

---

## 🗄️ Key DB Queries

```sql
-- CMV por unidade (mês atual)
SELECT * FROM vw_units_cmv_ranking;

-- Dashboard executivo
SELECT * FROM vw_executive_dashboard;

-- Alertas ativos
SELECT * FROM alerts WHERE resolved = FALSE ORDER BY created_at DESC;

-- Payback de uma unidade
SELECT fn_unit_payback('DVR-SP-001');
```

---

## 🔌 MCP Servers Available

| Server | Tools | Purpose |
|--------|-------|---------|
| `claude-flow` | 40+ | Swarm coordination, agent management |
| `ruv-swarm` | WASM | 2.8-4.4x speed, topology management |

---

## ⚙️ Environment Variables Required

```bash
ANTHROPIC_API_KEY=       # Required
POSTGRES_PASSWORD=       # Required
REDIS_PASSWORD=          # Required
RABBITMQ_PASSWORD=       # Required
WHATSAPP_TOKEN=          # Optional (mock mode if absent)
META_ADS_TOKEN=          # Optional
GOOGLE_SHEETS_CREDS=     # Optional (base64 JSON)
```

---

## 🧪 Testing an Agent

```python
import asyncio
from cmv_agent import CMVAgent

async def test():
    agent = CMVAgent()
    result = await agent.analyze("Qual o CMV da rede este mês?", user="test")
    print(result)

asyncio.run(test())
```

---

## 📌 Conventions

- **Async everywhere** (`asyncio`, `asyncpg`, `redis.asyncio`, `aio_pika`)
- **Portuguese** for business strings, **English** for code identifiers
- **Pydantic v2** for FastAPI models
- **f-strings** only (no `.format()` or `%`)
- **Type hints** on all function signatures
- DB queries **before** Claude calls — never hallucinate data
