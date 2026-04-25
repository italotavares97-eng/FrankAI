# 🎯 Frank AI OS — Davvero Gelato Intelligence Platform

> Sistema Multi-Agentes de Inteligência Empresarial para redes de franquias.  
> CEO Orchestrator com 9 agentes setoriais rodando em paralelo via `asyncio.gather()`.

[![Deploy](https://img.shields.io/badge/deploy-Docker-blue?logo=docker)](deploy/docker/)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](src/main.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🌐 [Live Demo — GitHub Pages](https://italotavares97-eng.github.io/FrankAI/)

---

## ✨ Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| 🎯 **CEO Orchestrator** | Orquestra 9 diretores em paralelo — nunca sequencial |
| 🔴 **CEO Rules Engine** | CMV ≤ 30%, EBITDA ≥ 10%, Aluguel ≤ 12%, Payback ≤ 30m, ROI ≥ 1.5x |
| 📊 **Relatórios HTML/PDF** | Briefing matinal, DRE semanal, consolidado mensal |
| 🔮 **Forecast 30/60/90d** | BI Agent com tendências, anomalias e correlações |
| 💾 **Memory System** | AgentMemory, DecisionLog, InsightHistory persistentes |
| 📧 **Notificações** | Email (SMTP), WhatsApp (Z-API), alertas em tempo real |
| ⚙️ **Automação** | Celery + RedBeat + Airflow DAGs (diário/semanal/mensal) |
| 🐳 **Docker Deploy** | Stack completa com 1 comando |

---

## 🏗️ Estrutura do Projeto

```
FrankAI/
├── src/                        ← Código FastAPI (novo sistema)
│   ├── main.py                 ← App factory
│   ├── agents/                 ← 9 agentes setoriais + CEO
│   ├── connectors/             ← Sults ERP, Meta Ads, WhatsApp, LinkedIn
│   ├── core/                   ← Config, DB, Redis, Logging
│   ├── memory/                 ← Models SQLAlchemy + MemoryService
│   ├── routes/                 ← FastAPI routers
│   ├── services/               ← Alert, Report, Decision services
│   └── tasks/                  ← Celery app + task definitions
├── deploy/
│   ├── docker/                 ← docker-compose.yml + Dockerfile
│   ├── airflow/                ← DAGs diário, semanal, mensal
│   └── migrations/             ← init.sql (schema PostgreSQL)
├── docs/                       ← GitHub Pages (site público)
│   ├── index.html              ← Landing page Frank Design System
│   └── pickaxe/                ← Config chatbot Pickaxe
├── sectors/                    ← Implementação legada por setor
├── integrations/               ← Conectores v1
└── .env.example                ← Template de variáveis de ambiente
```

---

## 🚀 Deploy Rápido

```bash
# 1. Clonar
git clone https://github.com/italotavares97-eng/FrankAI.git
cd FrankAI

# 2. Configurar variáveis
cp .env.example .env
# Editar .env com suas credenciais:
#   ANTHROPIC_API_KEY=sk-ant-...
#   POSTGRES_PASSWORD=sua_senha
#   SULTS_API_KEY=...

# 3. Subir stack completa
docker compose -f deploy/docker/docker-compose.yml up -d

# 4. Aplicar schema do banco
docker exec frank_postgres psql -U frank -d frank_db -f /migrations/init.sql
```

**Serviços disponíveis:**
| Serviço | URL |
|---------|-----|
| API | http://localhost:8000 |
| Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |
| Airflow | http://localhost:8080 |

---

## 🤖 Os 9 Agentes

| Agente | Especialidade |
|--------|--------------|
| 💰 **CFO** | CMV, EBITDA, DRE, fluxo de caixa · Sults ERP |
| ⚙️ **COO** | NPS, auditoria qualidade (0-100), SOP, throughput |
| 📣 **CMO** | Meta Ads ROAS, Instagram, CRM, pipeline B2B LinkedIn |
| ⚖️ **Legal** | Contratos, COF Lei 13.966/2019, eSocial, INPI |
| 👥 **RH** | Headcount, turnover, treinamentos, eNPS, CLT |
| 🗺️ **CSO** | Pipeline expansão, scoring leads, GO/NO-GO |
| 📦 **Supply** | Estoque, desperdício, score de fornecedores |
| 🧠 **BI** | Tendências 8 semanas, forecast 30d, anomalias |
| 🏗️ **Impl.** | Aberturas, checklists GO-LIVE, timeline 14 semanas |

---

## 🔑 CEO Hard Rules

```python
CMV          ≤ 30%      # Custo de Mercadorias Vendidas
EBITDA       ≥ 10%      # Resultado operacional
Aluguel      ≤ 12%      # Custo de ocupação
Payback      ≤ 30 meses # Retorno do investimento inicial
ROI 24m      ≥ 1.5x     # Múltiplo do capital em 24 meses
```

---

## 🌐 Rede Davvero Gelato

7 unidades monitoradas: `DVR-SP-001` · `DVR-SP-002` · `DVR-SP-003` · `DVR-SP-004` · `DVR-RJ-001` · `DVR-MG-001` · `DVR-RS-001`

---

## ⚙️ Stack Técnico

`FastAPI` · `PostgreSQL 16` · `Redis 7` · `Celery` · `RedBeat` · `Apache Airflow` · `Docker` · `Claude 3.5 Sonnet` · `SQLAlchemy Async` · `asyncpg` · `tenacity` · `structlog` · `aiosmtplib`

---

## 📄 Licença

MIT © 2026 Davvero Gelato Franchising
