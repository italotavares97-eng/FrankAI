# 🎯 FRANK AI OS — SISTEMA DE GESTÃO CEO
## Davvero Gelato Franchising · Todos os Setores · v1.0 · 2026

> **CEO Orchestrator rodando em paralelo:**  
> CFO · COO · CMO · Legal · RH · CSO · Supply · BI · Impl. → `asyncio.gather()`

---

## ÍNDICE

1. [Arquitetura do Sistema de Gestão](#1-arquitetura)
2. [CFO — Financeiro](#2-cfo)
3. [COO — Operações](#3-coo)
4. [CMO — Marketing](#4-cmo)
5. [Legal — Jurídico & Compliance](#5-legal)
6. [RH — Pessoas & Cultura](#6-rh)
7. [CSO — Expansão Estratégica](#7-cso)
8. [Supply — Suprimentos & Estoque](#8-supply)
9. [BI — Inteligência & Dados](#9-bi)
10. [Impl. — Implementação de Unidades](#10-impl)
11. [Gestão à Vista — CEO Dashboard](#11-gestao-a-vista)
12. [Cadência de Acompanhamentos](#12-cadencia)
13. [Sistema de Planos de Ação 5W2H](#13-planos-de-acao)
14. [Controles Corretivos & Escalonamento](#14-corretivos)

---

## 1. ARQUITETURA DO SISTEMA DE GESTÃO

### 1.1 CEO Hard Rules — Inegociáveis

| # | Regra | Limite | Medição | Ação se violado |
|---|-------|--------|---------|-----------------|
| R1 | CMV (Custo Mercadorias) | ≤ 30% receita bruta | Diário via ERP | Auditoria imediata + 5W2H em 24h |
| R2 | EBITDA | ≥ 10% receita bruta | Semanal/Mensal | Revisão DRE + corte de despesas |
| R3 | Aluguel | ≤ 12% receita bruta | Mensal | Renegociação ou relocação |
| R4 | Payback | ≤ 30 meses | Por unidade | Revisão projeções + plano de aceleração |
| R5 | ROI 24 meses | ≥ 1.5x capital investido | Por unidade | Revisão modelo operacional |

### 1.2 Pilares do Sistema

```
PLANEJAR → EXECUTAR → CONTROLAR → CORRIGIR → APRENDER
    ↑                                               ↓
    └───────────── PADRONIZAR (SOP) ←──────────────┘
```

### 1.3 Cadência Operacional CEO

| Frequência | Ritual | Participantes | Output |
|------------|--------|---------------|--------|
| **Diária** 07h00 | Briefing Morning | CEO + Frank AI | Dashboard 24h, alertas críticos |
| **Diária** 19h00 | Evening Analysis | CEO | Desvios do dia, ações corretivas |
| **Semanal** 2ª 08h00 | Review Semanal | CEO + Diretores | DRE semanal, top 3 prioridades |
| **Quinzenal** | Gestão à Vista | CEO + Gerentes | Painel físico atualizado |
| **Mensal** dia 1 | Consolidado | Todos | Relatório mensal, metas próximo mês |
| **Trimestral** | OKR Review | CEO + Board | Revisão estratégia, ajustes anuais |

---

## 2. CFO — FINANCEIRO

### 2.1 Meta (Targets)

| Indicador | Excelente | OK | Crítico | Meta 2026 |
|-----------|-----------|-----|---------|-----------|
| CMV rede | < 24% | 24-30% | > 30% | 24% |
| EBITDA rede | > 18% | 10-18% | < 10% | 18% |
| Receita/unidade | > R$100k | R$60-100k | < R$60k | R$85k média |
| Inadimplência royalties | 0% | < 5% | > 5% | 0% |
| Fluxo de caixa | Positivo 60d | Positivo 30d | Negativo | +60 dias |
| Giro de contas pagar | > 30 dias | 15-30 dias | < 15 dias | 35 dias |

### 2.2 Método

**DRE Padronizada por Unidade:**
```
(+) Receita Bruta
(-) Impostos (~13,5% Simples)
(=) Receita Líquida
(-) CMV (meta ≤ 24%)
(=) Lucro Bruto
(-) Despesas Operacionais
    - Aluguel (meta ≤ 12%)
    - Folha (meta ≤ 25%)
    - Marketing (meta 2-7%)
    - Royalties (5% + 2% fundo)
    - Manutenção (meta ≤ 2%)
    - Outros (meta ≤ 3%)
(=) EBITDA (meta ≥ 10%)
(-) Depreciação
(=) EBIT
(-) Resultado Financeiro
(=) Lucro Líquido
```

**Processo CMV:**
1. ERP Sults exporta vendas diárias por SKU
2. Frank AI calcula CMV teórico vs. realizado
3. Desvio > 2 pp → alerta automático ao franqueado
4. Desvio > 5 pp → auditoria presencial em 72h
5. Correção documentada em 5W2H

### 2.3 Padronização

- **SOP-FIN-001**: Fechamento de caixa diário (até 23h59)
- **SOP-FIN-002**: Conciliação bancária semanal (toda 2ª feira)
- **SOP-FIN-003**: DRE enviada ao sistema até dia 3 de cada mês
- **SOP-FIN-004**: Compras acima de R$2.000 requerem 3 orçamentos
- **SOP-FIN-005**: Pagamento de royalties até dia 10 de cada mês

### 2.4 Indicadores CFO

| KPI | Fórmula | Frequência | Owner | Alerta |
|-----|---------|------------|-------|--------|
| CMV% | (Custo produtos) / Receita bruta | Diário | Franqueado | > 28% |
| EBITDA% | EBITDA / Receita bruta | Mensal | CFO Frank | < 12% |
| Ticket médio | Receita / N° transações | Diário | COO Frank | < R$42 |
| Receita/m² | Receita / Área loja | Mensal | CFO Frank | < R$3.500/m² |
| Cobertura de caixa | Caixa disponível / Despesas mensais | Semanal | CFO Frank | < 1.5x |
| ROI acumulado | Lucro acumulado / Investimento inicial | Trimestral | CFO Frank | < 1.0x 12m |

### 2.5 Acompanhamentos CFO

**Diário (automático Frank AI):**
- Vendas vs. meta diária (% atingimento)
- CMV do dia (ERP Sults)
- Alertas de desvio > threshold

**Semanal (Segunda 08h):**
- DRE parcial da semana
- Comparativo semana anterior / mesmo período ano anterior
- Top 3 unidades + bottom 3 unidades
- Inadimplência de royalties

**Mensal (Dia 1-3):**
- DRE consolidada da rede
- Análise de variância orçado vs. realizado
- Projeção 3 meses (rolling forecast)
- CEO Rules compliance scorecard

### 2.6 Plano de Ação CMV Elevado (Template 5W2H)

| Campo | Conteúdo |
|-------|---------|
| **What** | Reduzir CMV de [X%] para ≤ 28% em 30 dias |
| **Why** | Violação CEO Rule R1: CMV > 30% compromete sustentabilidade |
| **Who** | Franqueado + Gerente de loja + Supply Frank |
| **Where** | Unidade [DVR-XX-00X] |
| **When** | Início imediato, meta em D+30, revisão D+15 |
| **How** | 1) Auditoria de fichas técnicas 2) Controle de porcionamento 3) Inventário surpresa 3x/semana 4) Revisão de fornecedores 5) Treinamento equipe |
| **How much** | R$800 (treinamento + auditoria) |

### 2.7 Controles Corretivos CFO

| Gatilho | Severidade | Ação | Prazo |
|---------|-----------|------|-------|
| CMV > 30% | 🔴 Crítico | Auditoria imediata + 5W2H | 24h |
| CMV 28-30% | ⚠️ Atenção | Alerta + diagnóstico | 72h |
| EBITDA < 10% | 🔴 Crítico | Revisão DRE + corte despesas | 48h |
| Royalties em atraso > 15d | ⚠️ Atenção | Notificação + negociação | 48h |
| Receita < R$50k/mês | 🔴 Crítico | Plano de recuperação emergencial | 7 dias |

---

## 3. COO — OPERAÇÕES

### 3.1 Meta

| Indicador | Excelente | OK | Crítico | Meta 2026 |
|-----------|-----------|-----|---------|-----------|
| NPS rede | > 75 | 50-75 | < 50 | 78 |
| Auditoria qualidade | > 90/100 | 75-90 | < 75 | 88 |
| Throughput (clientes/hora) | > 45 | 30-45 | < 30 | 42 |
| Tempo médio atendimento | < 3 min | 3-5 min | > 5 min | 2,5 min |
| Desperdício produto | < 3% receita | 3-5% | > 5% | 2,5% |
| Abertura no horário | 100% | 95-100% | < 95% | 100% |

### 3.2 Método

**Checklist Operacional Diário (SOP-OPS-001):**
```
ABERTURA (antes das 11h00)
□ Limpeza de máquinas verificada
□ Temperaturas dos vitrines: -12°C a -15°C
□ Estoque de potes/copinhos verificado
□ Caixa aberto com troco R$150
□ Uniforme da equipe (completo, limpo)
□ Sabores disponíveis ≥ 18 (de 24 possíveis)

DURANTE OPERAÇÃO
□ Reposição de vitrine a cada 2 horas
□ Limpeza de bancada a cada 30 min
□ Temperatura monitorada 3x/dia (9h, 14h, 19h)

FECHAMENTO (até 30 min após encerramento)
□ Caixa fechado e conferido
□ Sobras de gelato pesadas e registradas
□ Máquinas higienizadas
□ Estoque contado e lançado no ERP
□ Relatório de vendas enviado via WhatsApp Frank
```

**Ciclo PDCA Operacional:**
- **P (Plan)**: Meta diária de vendas definida no briefing 07h
- **D (Do)**: Execução conforme SOPs
- **C (Check)**: Frank AI monitora ERP em tempo real; NPS coletado pós-venda
- **A (Act)**: Desvios geram alertas automáticos + plano corretivo

### 3.3 Padronização

- **SOP-OPS-001**: Checklist abertura/fechamento (digital no sistema)
- **SOP-OPS-002**: Protocolo de temperatura e armazenamento
- **SOP-OPS-003**: Atendimento ao cliente (script + fluxo)
- **SOP-OPS-004**: Higienização de equipamentos (ANVISA)
- **SOP-OPS-005**: Gestão de desperdício e fichas técnicas
- **SOP-OPS-006**: Auditoria de qualidade (100 pontos) — trimestral

### 3.4 Indicadores COO

| KPI | Fórmula | Frequência | Owner | Alerta |
|-----|---------|------------|-------|--------|
| NPS | (Promotores - Detratores) / Total × 100 | Diário | COO Frank | < 60 |
| Score auditoria | Pontuação checklist 100pts | Trimestral | COO Frank | < 80 |
| Throughput | Clientes atendidos / Horas abertas | Diário | Gerente | < 30/h |
| Desperdício | (Perdas) / Compras | Semanal | Gerente | > 4% |
| Abertura pontual | Dias no horário / Dias abertos | Mensal | Franqueado | < 98% |
| Reclamações | N° reclamações / 1000 atendimentos | Mensal | COO Frank | > 5 |

### 3.5 Acompanhamentos COO

**Diário:** NPS automático (SMS pós-compra) + throughput ERP  
**Semanal:** Consolidado NPS + revisão temperatura + desperdício  
**Quinzenal:** Visita técnica surpresa (amostral — 2 unidades/quinzena)  
**Trimestral:** Auditoria formal 100 pontos + relatório ao franqueado

### 3.6 Auditoria de Qualidade — 100 Pontos

| Categoria | Peso | Itens Avaliados |
|-----------|------|-----------------|
| Segurança Alimentar (ANVISA) | 25 pts | Temperatura, validade, higiene manipuladores |
| Padrão Visual da Loja | 20 pts | Vitrine, fachada, uniformes, organização |
| Qualidade do Produto | 20 pts | Textura, sabor, porcionamento, apresentação |
| Atendimento ao Cliente | 20 pts | Tempo, cordialidade, conhecimento produto |
| Processos Administrativos | 15 pts | Caixa, estoque, relatórios, treinamentos |

### 3.7 Controles Corretivos COO

| Gatilho | Severidade | Ação | Prazo |
|---------|-----------|------|-------|
| NPS < 50 | 🔴 Crítico | Visita técnica + diagnóstico CX | 48h |
| Temperatura fora do range | 🔴 Crítico | Isolamento produto + manutenção | Imediato |
| Score auditoria < 75 | 🔴 Crítico | Plano corretivo + nova auditoria 30d | 7 dias |
| Desperdício > 5% | ⚠️ Atenção | Revisão fichas técnicas + treinamento | 5 dias |
| Fechamento irregular | ⚠️ Atenção | Notificação ao franqueado | 24h |

---

## 4. CMO — MARKETING

### 4.1 Meta

| Indicador | Excelente | OK | Crítico | Meta 2026 |
|-----------|-----------|-----|---------|-----------|
| ROAS Meta Ads | > 4.0x | 2.5-4.0x | < 2.5x | 3.8x |
| CPA (custo por aquisição) | < R$18 | R$18-35 | > R$35 | R$20 |
| Seguidores Instagram (rede) | +5%/mês | +2-5% | < 2% | +3,5%/mês |
| Taxa engajamento IG | > 4% | 2-4% | < 2% | 4,5% |
| Leads B2B/mês | > 15 | 8-15 | < 8 | 12 |
| Taxa conversão lead→contrato | > 15% | 8-15% | < 8% | 12% |

### 4.2 Método

**Flywheel B2C — Operação Semanal:**
```
ATTRACT (Conteúdo orgânico)
  Mon: Feed educativo "Como é feito o gelato"
  Wed: Reels produto / bastidores
  Fri: Stories interativos (enquete de sabor)

ENGAGE (Comunidade)
  Daily: Resposta a comentários < 2h
  Semanal: UGC reshare de clientes
  Quinzenal: Live ou Q&A

DELIGHT (Experiência)
  Mensal: Oferta exclusiva para seguidores
  Trimestral: Evento clube de clientes

ADVOCATE (Embaixadores)
  Ongoing: Programa de indicação
  Mensal: Spotlight de cliente fiel
```

**Meta Ads — Estrutura de Campanha:**
```
Campanha: Awareness Davvero
  ├── Adset: Lookalike 2% (base compradores)
  ├── Adset: Interesse premium/artesanal
  └── Adset: Retargeting visitantes site

Campanha: Conversão (Delivery/Loja)
  ├── Adset: 5km raio de cada loja
  ├── Adset: Retargeting engajamento 30d
  └── Adset: Clientes inativos 60d
```

### 4.3 Padronização

- **SOP-MKT-001**: Identidade visual (logo, cores, fontes, tom de voz)
- **SOP-MKT-002**: Calendário editorial mensal (publicado até dia 25 do mês anterior)
- **SOP-MKT-003**: Processo de aprovação de conteúdo (franqueado → CMO → publica)
- **SOP-MKT-004**: Resposta a crise/comentário negativo (máx. 1h)
- **SOP-MKT-005**: Briefing de campanha paga (template preenchido antes de ativar)
- **SOP-MKT-006**: Relatório mensal Meta Ads (enviado até dia 5)

### 4.4 Indicadores CMO

| KPI | Frequência | Owner | Threshold crítico |
|-----|------------|-------|-------------------|
| ROAS por campanha | Diário | CMO Frank | < 2.0x |
| CPM (custo/1000 impressões) | Semanal | CMO Frank | > R$45 |
| CTR (click-through rate) | Semanal | CMO Frank | < 1.2% |
| Impressões orgânicas | Semanal | CMO Frank | Queda > 20% |
| Leads LinkedIn (B2B) | Semanal | CMO Frank | < 2/semana |
| Revenue atribuído ao MKT | Mensal | CFO+CMO | < 8x budget |

### 4.5 Acompanhamentos CMO

**Diário:** ROAS e budget consumido Meta Ads (Frank AI automático)  
**Semanal:** Performance por criativo + engajamento orgânico  
**Quinzenal:** Pipeline B2B LinkedIn + taxa conversão leads  
**Mensal:** ROI global de marketing + planejamento próximo mês

### 4.6 Controles Corretivos CMO

| Gatilho | Ação | Prazo |
|---------|------|-------|
| ROAS < 2.5x por 3 dias | Pausar adset + revisar criativo | 24h |
| CPA > R$40 | Rever segmentação + landing page | 48h |
| Engajamento IG queda > 30% | Análise algoritmo + teste de formato | 72h |
| Comentário negativo viral | Protocolo crise CMO | 1h |

---

## 5. LEGAL — JURÍDICO & COMPLIANCE

### 5.1 Meta

| Indicador | Meta | Crítico |
|-----------|------|---------|
| COF atualizado | Anual (Lei 13.966/2019) | Desatualizado > 1 ano |
| Contratos vigentes sem pendência | 100% | < 95% |
| Certidões negativas (CNPJ) | Todas em dia | Qualquer débito |
| Registros INPI (marca) | 100% registrado | Sem registro |
| Auditorias ANVISA sem embargo | 100% | Qualquer embargo |
| Processos trabalhistas ativos | < 3/ano rede | > 5/ano |

### 5.2 Método

**Ciclo de Compliance Legal:**
```
JAN: Revisão COF + atualização anual
FEV: Auditorias internas ANVISA (todas unidades)
MAR: Renovação de alvarás e licenças
ABR: Revisão de contratos de fornecedores
MAI: Treinamento RH → CLT + eSocial
JUN: Auditoria LGPD (dados de clientes)
JUL: Relatório semestral compliance
AGO: Revisão de seguros (RC, patrimonial)
SET: Renovação de contratos franqueados (5 anos)
OUT: Atualização de SOPs legais
NOV: Planejamento tributário próximo ano
DEZ: Fechamento legal + relatório anual
```

### 5.3 Padronização

- **SOP-LEG-001**: Due diligence novo franqueado (30 dias pré-assinatura)
- **SOP-LEG-002**: Entrega do COF (10 dias antes de qualquer contrato)
- **SOP-LEG-003**: Protocolo de resposta a fiscalizações (ANVISA/Procon)
- **SOP-LEG-004**: Gestão de processos trabalhistas (notificação 24h)
- **SOP-LEG-005**: LGPD — consentimento de dados de clientes
- **SOP-LEG-006**: Renovação/rescisão de contratos de franquia

### 5.4 Indicadores Legal

| KPI | Frequência | Owner | Alerta |
|-----|------------|-------|--------|
| % contratos regularizados | Mensal | Legal Frank | < 100% |
| Prazo renovação COF | Anual | Legal Frank | < 60d do vencimento |
| N° processos trabalhistas | Trimestral | Legal Frank | > 2 novos/trimestre |
| Pendências ANVISA | Mensal | Legal Frank | Qualquer pendência |
| Provisionamento jurídico | Trimestral | CFO+Legal | > R$50k provisionado |

### 5.5 Controles Corretivos Legal

| Gatilho | Ação | Prazo |
|---------|------|-------|
| Embargo ANVISA | Suspensão operação + plano corretivo | Imediato |
| Processo trabalhista novo | Notificação CEO + advogado | 24h |
| COF desatualizado | Atualização compulsória | 30 dias |
| Franqueado sem registro | Notificação formal + prazo | 15 dias |

---

## 6. RH — PESSOAS & CULTURA

### 6.1 Meta

| Indicador | Excelente | OK | Crítico | Meta 2026 |
|-----------|-----------|-----|---------|-----------|
| Turnover mensal | < 3% | 3-8% | > 8% | 4% |
| eNPS (colaboradores) | > 40 | 20-40 | < 20 | 45 |
| % equipe treinada (Davvero Academy) | 100% | 85-100% | < 85% | 100% |
| Tempo médio contratação | < 10 dias | 10-20 dias | > 20 dias | 8 dias |
| Absenteísmo | < 2% | 2-5% | > 5% | 1,8% |
| Headcount ideal/unidade | 4-6 pessoas | 3-4 | < 3 | 5 |

### 6.2 Método

**Ciclo de Vida do Colaborador:**
```
ATRAÇÃO → SELEÇÃO → ONBOARDING → TREINAMENTO → PERFORMANCE → RETENÇÃO
    ↑                                                               ↓
    └─────────────────── CULTURA DAVVERO ──────────────────────────┘
```

**Onboarding Padrão (21 dias):**
- D1-3: Cultura Davvero + CEO Rules + handbook
- D4-7: Treinamento produto (gelato, sabores, origem)
- D8-14: Treinamento operacional (equipamentos, SOPs, caixa)
- D15-21: Shadowing + prática supervisionada
- D21: Certificação Davvero Academy (mínimo 80%)

**Avaliação de Performance (Semestral):**
- Autoavaliação + avaliação do gerente (180°)
- 5 competências: Produto, Atendimento, Processo, Equipe, Resultado
- Resultado: Desenvolvimento | Manutenção | Reconhecimento
- PDI (Plano de Desenvolvimento Individual) para todos

### 6.3 Padronização

- **SOP-RH-001**: Processo seletivo padrão (triagem → teste → entrevista → admissão)
- **SOP-RH-002**: Onboarding 21 dias (presencial + digital Davvero Academy)
- **SOP-RH-003**: Avaliação semestral de performance (junho e dezembro)
- **SOP-RH-004**: Protocolo de demissão (CLT + comunicação ao franqueado)
- **SOP-RH-005**: eSocial — eventos mensais (admissão, demissão, férias, afastamento)
- **SOP-RH-006**: Pesquisa de clima trimestral (eNPS)

### 6.4 Indicadores RH

| KPI | Fórmula | Frequência | Owner | Alerta |
|-----|---------|------------|-------|--------|
| Turnover | (Demitidos / Headcount médio) × 100 | Mensal | RH Frank | > 6% |
| eNPS | (Promotores - Detratores) / Total | Trimestral | RH Frank | < 30 |
| % certificados | Certificados / Headcount total | Mensal | RH Frank | < 90% |
| Absenteísmo | (Faltas) / (Headcount × dias úteis) | Mensal | Gerente | > 3% |
| Custo folha / Receita | (Folha total) / Receita bruta | Mensal | CFO+RH | > 28% |
| Tempo até primeira venda | D do onboarding até venda solo | Por contratação | Gerente | > 21d |

### 6.5 Controles Corretivos RH

| Gatilho | Ação | Prazo |
|---------|------|-------|
| Turnover > 8% unidade | Diagnóstico clima + entrevista demitidos | 7 dias |
| eNPS < 20 | Workshop clima + plano de melhoria | 15 dias |
| Absenteísmo > 5% | Conversa individual + gestão presença | 48h |
| Headcount < mínimo (3) | Contratação emergencial | 5 dias |

---

## 7. CSO — EXPANSÃO ESTRATÉGICA

### 7.1 Meta

| Indicador | Meta 2026 | Crítico |
|-----------|-----------|---------|
| Novas unidades abertas | 3 | < 1 |
| Pipeline qualificados | 15 leads/mês | < 8 |
| Taxa conversão lead → contrato | 12% | < 6% |
| Tempo lead → abertura | 6 meses | > 9 meses |
| Score GO/NO-GO (mínimo) | ≥ 70/100 | < 60 |
| Custo de aquisição franqueado | < R$12.000 | > R$20.000 |

### 7.2 Método

**Funil de Expansão (Flywheel):**
```
GERAÇÃO DE LEADS
  → LinkedIn Ads (B2B) + Feiras de franquias + Indicações
  → Qualificação: capital mínimo R$250k + perfil empreendedor

QUALIFICAÇÃO (Score 0-100)
  → Financeiro (30pts): capital, renda, crédito
  → Perfil (25pts): experiência, disponibilidade, região
  → Localização (25pts): praça, concorrência, fluxo
  → Motivação (20pts): alinhamento com valores Davvero

VIABILIDADE (GO/NO-GO)
  → CFO: projeções 24 meses, payback, ROI
  → Legal: análise contratual, due diligence
  → Supply: capacidade de atendimento
  → CSO: análise de mercado e concorrência

CONTRATO & IMPLEMENTAÇÃO
  → Assinatura COF → Aguardar 10 dias → Assinatura contrato
  → Handover para Implementação (14 semanas até GO-LIVE)
```

### 7.3 Padronização

- **SOP-CSO-001**: Scoring de leads (formulário padrão 100 pontos)
- **SOP-CSO-002**: Processo GO/NO-GO (análise paralela 4 agentes)
- **SOP-CSO-003**: Apresentação Davvero (pitch deck + tour virtual)
- **SOP-CSO-004**: Análise de praça (fluxo, concorrência, demographics)
- **SOP-CSO-005**: Carta de intenção + NDA antes de revelar dados financeiros

### 7.4 Indicadores CSO

| KPI | Frequência | Owner | Alerta |
|-----|------------|-------|--------|
| Leads gerados | Semanal | CSO Frank | < 3/semana |
| Leads qualificados (score > 60) | Mensal | CSO Frank | < 30% do total |
| Propostas enviadas | Mensal | CSO Frank | < 3/mês |
| Taxa conversão | Trimestral | CSO+CEO | < 8% |
| Pipeline revenue projetado | Mensal | CSO+CFO | — |
| NPS pós-abertura (novo franqueado) | Pós-abertura | CSO Frank | < 60 |

### 7.5 Scorecard GO/NO-GO

| Dimensão | Peso | Dados necessários |
|----------|------|------------------|
| Viabilidade financeira (CFO) | 35% | DRE projetada, payback, ROI |
| Análise de mercado (CSO) | 25% | Concorrência, fluxo, demographics |
| Compliance legal (Legal) | 20% | Due diligence, CNPJ, scoring crédito |
| Capacidade supply chain (Supply) | 20% | Distância base, lead time, capacidade |

**Veredito:**
- ≥ 80: ✅ GO — avançar imediatamente
- 65-79: ⏸ WAIT — condicionais a resolver
- < 65: ❌ NO-GO — repriorizar praça

---

## 8. SUPPLY — SUPRIMENTOS & ESTOQUE

### 8.1 Meta

| Indicador | Excelente | OK | Crítico | Meta 2026 |
|-----------|-----------|-----|---------|-----------|
| Fill rate (pedidos entregues completos) | > 98% | 92-98% | < 92% | 98% |
| Giro de estoque | > 12x/ano | 8-12x | < 8x | 14x |
| Desperdício de insumos | < 2% | 2-4% | > 4% | 1,8% |
| Lead time médio (pedido→entrega) | < 2 dias | 2-4 dias | > 4 dias | 1,5 dias |
| Score fornecedores (médio) | > 85/100 | 70-85 | < 70 | 88 |
| Ruptura de estoque (incidentes) | 0 | 1-2/mês | > 3/mês | 0 |

### 8.2 Método

**Ciclo de Suprimentos:**
```
PLANEJAMENTO DE COMPRAS
  → Forecast de demanda (BI Agent, rolling 4 semanas)
  → Ponto de pedido = Demanda média × Lead time + Estoque de segurança
  → Pedido gerado automaticamente quando estoque < ponto de pedido

RECEBIMENTO (SOP-SUP-002)
  → Conferência de NF vs. pedido
  → Verificação temperatura (embalados < 0°C, resfriados < 4°C)
  → Registro no ERP Sults (lote, validade, quantidade)
  → Armazenamento PEPS (primeiro que entra, primeiro que sai)

CONTROLE DE ESTOQUE
  → Inventário diário (gelato e embalagens)
  → Inventário semanal (insumos completo)
  → Inventário mensal (auditoria completa com CMV)

AVALIAÇÃO DE FORNECEDORES (Trimestral)
  → Qualidade: 40pts (conformidade, temperatura, validade)
  → Prazo: 30pts (on-time delivery, fill rate)
  → Preço: 20pts (competitividade)
  → Relacionamento: 10pts (suporte, comunicação)
```

### 8.3 Padronização

- **SOP-SUP-001**: Pedido padrão (template ERP por categoria de produto)
- **SOP-SUP-002**: Recebimento com verificação de temperatura e NF
- **SOP-SUP-003**: Armazenamento PEPS com etiquetagem de lote
- **SOP-SUP-004**: Inventário diário/semanal/mensal (formulário padrão)
- **SOP-SUP-005**: Avaliação trimestral de fornecedores (scorecard 100pts)
- **SOP-SUP-006**: Gestão de não conformidades (produto fora do padrão)

### 8.4 Indicadores Supply

| KPI | Fórmula | Frequência | Owner | Alerta |
|-----|---------|------------|-------|--------|
| Fill rate | Itens entregues / Itens pedidos | Por entrega | Supply Frank | < 95% |
| Giro estoque | Custo produtos vendidos / Estoque médio | Mensal | Supply Frank | < 10x |
| Acuracidade inventário | (Físico = Sistema) / Total itens | Semanal | Gerente | < 95% |
| Ruptura de gelato | Incidentes de falta de produto | Diário | Gerente | Qualquer |
| CMV insumos | Custo real / Custo teórico (fichas) | Mensal | Supply+CFO | > 110% |
| Score fornecedor | Scorecard 100pts | Trimestral | Supply Frank | < 70 |

### 8.5 Controles Corretivos Supply

| Gatilho | Ação | Prazo |
|---------|------|-------|
| Ruptura de gelato | Pedido emergencial + comunicação loja | 2h |
| Temperatura de entrega fora spec | Recusa + não conformidade + fornecedor | Imediato |
| Fill rate < 90% | Reunião fornecedor + fornecedor backup | 48h |
| Score fornecedor < 65 | Notificação + prazo de melhoria 60 dias | 5 dias |
| Desvio CMV > 8% vs. ficha técnica | Auditoria porcionamento + recontagem | 24h |

---

## 9. BI — INTELIGÊNCIA & DADOS

### 9.1 Meta

| Indicador | Meta | Frequência |
|-----------|------|------------|
| Disponibilidade do dashboard | > 99,5% uptime | Contínuo |
| Latência de alertas | < 5 min do evento | Contínuo |
| Forecast accuracy (30d) | MAPE < 15% | Mensal |
| Anomalias detectadas proativamente | > 90% antes do CEO notar | Mensal |
| Correlações identificadas/mês | > 5 insights acionáveis | Mensal |
| Relatórios entregues no prazo | 100% | Mensal |

### 9.2 Método

**Pipeline de Dados:**
```
COLETA (Automática)
  ERP Sults → vendas, estoque, CMV (near-real-time)
  Meta Ads API → ROAS, CPA, impressões (diário)
  Google Analytics → tráfego, conversões (diário)
  NPS Sistema → pesquisas pós-compra (imediato)
  Planilhas RH → headcount, turnover (semanal)

PROCESSAMENTO
  Normalização → limpeza → enriquecimento
  Cálculo CEO Rules compliance score
  Detecção de anomalias (Z-score + ARIMA)
  Ranking de unidades por 12 KPIs

OUTPUT
  Dashboard tempo real (CEO + gerentes)
  Briefing morning (07h00)
  Alertas Push (WhatsApp + email)
  Relatórios HTML/PDF (semanal/mensal)
  Forecast rolling 30/60/90 dias
```

### 9.3 Padronização

- **SOP-BI-001**: Dicionário de dados (fonte única de verdade para cada KPI)
- **SOP-BI-002**: Nomenclatura de relatórios e versionamento
- **SOP-BI-003**: Protocolo de alerta (threshold → severidade → canal → prazo)
- **SOP-BI-004**: Revisão mensal de modelos de forecast
- **SOP-BI-005**: Auditoria de qualidade de dados (mensal)

### 9.4 Indicadores BI

| KPI | Meta | Frequência |
|-----|------|------------|
| Dados importados sem erro | > 99% | Diário |
| Alertas falso-positivo | < 5% do total | Mensal |
| Tempo resposta API BI | < 2s (p95) | Contínuo |
| Modelos retreinados | 1x/mês | Mensal |
| Insights adotados pelo CEO | > 60% | Trimestral |

### 9.5 Modelo de Forecast

**Variáveis de entrada:**
- Histórico de vendas 24 meses (por unidade, por dia da semana)
- Sazonalidade (verão +35%, datas especiais, feriados)
- Temperatura média (correlação +0.72 com vendas gelato)
- Eventos locais (shows, feriados, férias escolares)
- Ações de marketing ativas

**Output do BI Agent:**
```
Unidade: DVR-SP-001
Próximos 30 dias:
  Receita projetada: R$92.400 (±8%)
  CMV projetado: 24.1%
  EBITDA projetado: 19.2%
  Risco: ⚠️ Semana do Carnaval (-18% vendas histórico)
  Oportunidade: 🌡️ Temperatura >32°C em 12 dos 30 dias (+22% vendas)
```

---

## 10. IMPL. — IMPLEMENTAÇÃO DE UNIDADES

### 10.1 Meta

| Indicador | Meta | Crítico |
|-----------|------|---------|
| Abertura no prazo (14 semanas) | 100% | Qualquer atraso > 2 semanas |
| GO-LIVE checklist (100 itens) | 100% completo | < 90% |
| Custo de implementação vs. orçado | ±10% | > +20% |
| Receita mês 1 vs. projeção | > 80% | < 60% |
| NPS franqueado pós-abertura (30d) | > 70 | < 50 |
| Retrabalhos de obra | < 2 itens | > 5 itens |

### 10.2 Método — Cronograma 14 Semanas

| Semana | Fase | Atividades | Owner |
|--------|------|-----------|-------|
| S1-2 | Planejamento | Projeto arquitetônico, aprovações prefeitura, contratos obras | Impl. + Legal |
| S3-4 | Início obras | Reforma civil, instalações elétricas/hidráulicas | Impl. + Fornecedor |
| S5-7 | Obra avançada | Acabamentos, pintura, fachada, comunicação visual | Impl. |
| S8-9 | Equipamentos | Entrega/instalação: máquinas gelato, refrigeração, caixa | Supply + Impl. |
| S10-11 | TI e operacional | PDV, Wi-Fi, câmeras, ERP Sults, sistema NPS | Impl. |
| S12 | Treinamento | Davvero Academy (21 dias comprimido), SOPs, produto | RH + COO |
| S13 | Pré-abertura | Teste operacional, auditoria qualidade, estoque inicial | COO + Impl. |
| S14 | GO-LIVE | Abertura oficial, acompanhamento D+7 | CEO + Impl. |

### 10.3 GO-LIVE Checklist (100 Itens — Categorias)

| Categoria | N° Itens | Responsável |
|-----------|---------|-------------|
| Documentação legal (alvará, vigilância, INPI) | 18 | Legal |
| Instalações e equipamentos | 22 | Impl. |
| Estoque inicial e fornecedores | 15 | Supply |
| TI (PDV, ERP, câmeras, internet) | 12 | Impl. |
| Treinamento equipe certificado | 10 | RH |
| Marketing local (redes sociais, Google My Business) | 8 | CMO |
| Financeiro (caixa, conta bancária, royalties cadastrado) | 8 | CFO |
| Operacional (SOPs distribuídos, primeiros insumos) | 7 | COO |

### 10.4 Controles Corretivos Impl.

| Gatilho | Ação | Prazo |
|---------|------|-------|
| Atraso > 1 semana | Reunião crise + replanejamento | 24h |
| GO-LIVE checklist < 85% | Bloqueio de abertura | Imediato |
| Custo obra > 15% acima orçado | Autorização CEO obrigatória | Antes de continuar |
| Receita mês 1 < 60% projeção | Plano de recuperação emergencial | D+30 |

---

## 11. GESTÃO À VISTA — CEO DASHBOARD

### 11.1 Painel Físico (Sala de Guerra)

**Estrutura do quadro (atualizado a cada 15 dias):**

```
┌─────────────────────────────────────────────────────────────────┐
│  DAVVERO GELATO · GESTÃO À VISTA · [MÊS/ANO]                  │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   CEO RULES  │ REDE HOJE    │ ALERTAS      │ FOCO DO MÊS       │
│              │              │              │                     │
│ CMV ≤30%     │ R$X.XXX.XXX  │ 🔴 [unidade] │ ► [prioridade 1]  │
│ ████░░ 24%✅ │ (receita)    │ ⚠️ [unidade] │ ► [prioridade 2]  │
│              │              │              │ ► [prioridade 3]  │
│ EBITDA ≥10%  │ NPS: XX      │              │                     │
│ ██████ 17%✅ │ (rede média) │              │                     │
│              │              │              │                     │
│ ALUGUEL ≤12% │ 7 unidades   │              │                     │
│ ████░ 10%✅  │ XX% abaixo   │              │                     │
│              │ da meta      │              │                     │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│              RANKING DE UNIDADES (mês atual)                    │
│  #1 DVR-SP-003  R$103k  CMV23.8%  EBITDA21.4%  NPS78  ✅      │
│  #2 DVR-RJ-001  R$94k   CMV25.9%  EBITDA17.3%  NPS74  ✅      │
│  #3 DVR-SP-001  R$89k   CMV24.3%  EBITDA18.7%  NPS72  ✅      │
│  #4 DVR-SP-002  R$76k   CMV27.1%  EBITDA14.2%  NPS68  ✅      │
│  #5 DVR-RS-001  R$71k   CMV26.2%  EBITDA16.8%  NPS70  ✅      │
│  #6 DVR-MG-001  R$68k   CMV28.7%  EBITDA13.1%  NPS65  ⚠️     │
│  #7 DVR-SP-004  R$59k   CMV31.4%  EBITDA9.8%   NPS61  🔴     │
├─────────────────────────────────────────────────────────────────┤
│  PLANOS DE AÇÃO ATIVOS                                         │
│  DVR-SP-004: CMV 31.4% → Meta 28% até DD/MM · Owner: [nome]  │
│  DVR-MG-001: NPS 65 → Meta 70 até DD/MM · Owner: [nome]      │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Dashboard Digital (Frank AI — Tempo Real)

**Acesso:** `http://localhost:8000/` ou GitHub Pages  
**Atualização:** Near-real-time (ERP Sults → Frank AI → Dashboard)

**Tiles obrigatórios:**
- 💰 Receita rede (dia / semana / mês)
- 📊 CMV médio rede + destaque violações
- 📈 EBITDA médio rede
- 😊 NPS rede (últimos 7 dias)
- 🔴 Alertas ativos (contagem por severidade)
- 📣 ROAS Meta Ads (últimas 24h)
- 🏆 Ranking unidades (CMV + EBITDA + NPS)

---

## 12. CADÊNCIA DE ACOMPANHAMENTOS

### 12.1 Ritmo Operacional Completo

```
DIÁRIO (Frank AI automático)
  07:00 → Briefing morning (CEO + diretores AI)
  08:30 → Alertas críticos (WhatsApp CEO)
  19:00 → Evening analysis (desvios do dia)
  23:59 → Fechamento de caixa (ERP sync)

SEMANAL (2ª feira)
  08:00 → Review com DRE parcial
  ─ DRE semanal por unidade
  ─ Top 3 + Bottom 3 performances
  ─ Alertas abertos e planos em andamento
  ─ Definição de 3 prioridades da semana

QUINZENAL
  ─ Gestão à Vista (painel físico atualizado)
  ─ Visita técnica surpresa (2 unidades)
  ─ Pipeline de expansão review

MENSAL (dia 1-3)
  ─ DRE consolidada + CEO Rules scorecard
  ─ Revisão de todos os planos de ação
  ─ Atualização de metas próximo mês
  ─ Report para franqueados (individual por unidade)
  ─ Forecast 30/60/90 dias

TRIMESTRAL
  ─ OKR Review (estratégia e resultado)
  ─ Auditoria de qualidade (COO)
  ─ Avaliação de fornecedores (Supply)
  ─ Revisão de contratos vencendo
  ─ eNPS pesquisa colaboradores
  ─ Análise de expansão (CSO)

ANUAL
  ─ Planejamento estratégico (OKRs do ano)
  ─ Orçamento anual (budget por unidade)
  ─ Revisão do COF (Legal)
  ─ Avaliação 360° equipe HQ
  ─ Benchmarking do setor
```

### 12.2 Matriz de Reuniões

| Reunião | Frequência | Duração | Participantes | Output obrigatório |
|---------|------------|---------|---------------|--------------------|
| Morning Briefing | Diária | 15 min | CEO (+ Frank AI) | Top 3 ações do dia |
| Review Semanal | Semanal | 60 min | CEO + Diretores AI | Ata + planos atualizados |
| Gestão à Vista | Quinzenal | 30 min | CEO + Gerentes | Painel atualizado |
| Board Mensal | Mensal | 90 min | CEO + Franqueados | Relatório + metas |
| OKR Trimestral | Trimestral | 3h | CEO + Equipe HQ | OKRs revisados |

---

## 13. SISTEMA DE PLANOS DE AÇÃO 5W2H

### 13.1 Template Universal

```markdown
## PLANO DE AÇÃO — [CÓDIGO: PA-SETOR-NNN]
**Data abertura:** DD/MM/AAAA
**Unidade/Área:** DVR-XX-00X ou HQ
**Prioridade:** 🔴 Crítico | ⚠️ Médio | 🔵 Baixo
**Status:** Aberto | Em andamento | Concluído

| Campo | Resposta |
|-------|---------|
| **WHAT** — O que fazer? | [Ação específica e mensurável] |
| **WHY** — Por que fazer? | [Causa-raiz + impacto se não feito] |
| **WHO** — Quem é responsável? | [Nome + cargo] |
| **WHERE** — Onde executar? | [Unidade/área/processo] |
| **WHEN** — Quando? | Início: DD/MM · Meta: DD/MM · Review: DD/MM |
| **HOW** — Como fazer? | [Passo a passo das ações] |
| **HOW MUCH** — Quanto custa? | R$ [valor] ou Zero |

**Resultado esperado:** [Métrica antes → Meta]
**Resultado real:** [Preenchido na conclusão]
```

### 13.2 Planos de Ação por CEO Rule

**PA-CMV-001 — CMV Elevado:**
- Auditoria de fichas técnicas (± ficha vs. realizado)
- Inventário surpresa 3x/semana
- Treinamento de porcionamento (gramatura correta)
- Revisão de fornecedores (benchmarking de preços)
- Controle de desperdício (pesagem diária de sobras)

**PA-EBITDA-001 — EBITDA Abaixo:**
- Mapeamento de despesas (linha a linha da DRE)
- Corte de despesas não-essenciais (top 3 itens)
- Plano de aceleração de receita (vendas adicionais, delivery)
- Renegociação de contratos (aluguel, fornecedores)
- Meta de vendas diária aumentada em X%

**PA-NPS-001 — NPS Baixo:**
- Análise de verbatins (leitura dos comentários negativos)
- Visita técnica COO (auditoria operacional)
- Treinamento de atendimento (role-play equipe)
- Protocolo de recuperação de clientes (retorno de reclamações em 24h)
- Meta NPS: +10 pontos em 60 dias

**PA-TURN-001 — Turnover Alto:**
- Entrevistas de desligamento (todos os últimos 30 dias)
- Pesquisa de clima (eNPS urgente)
- Revisão de jornada e escalas
- Revisão de benefícios (vale-alimentação, uniforme, comissão)
- PDI para colaboradores de alto desempenho em risco

### 13.3 Controle de Planos Ativos

| PA# | Setor | Unidade | Meta | Responsável | Prazo | Status | % |
|-----|-------|---------|------|-------------|-------|--------|---|
| PA-CMV-001 | CFO | DVR-SP-004 | CMV 28% | [Gerente] | DD/MM | 🟡 | 40% |
| PA-NPS-001 | COO | DVR-MG-001 | NPS 70 | [Gerente] | DD/MM | 🟢 | 65% |

---

## 14. CONTROLES CORRETIVOS & ESCALONAMENTO

### 14.1 Matriz de Escalonamento

| Severidade | Critério | Notificação | Prazo resposta | Autoridade |
|-----------|----------|-------------|----------------|-----------|
| 🔴 **Crítico** | CEO Rule violada | CEO imediato (WhatsApp) | 2h | CEO decide |
| ⚠️ **Alto** | KPI 10% abaixo da meta | Diretor + CEO (email) | 24h | Diretor decide |
| 🟡 **Médio** | Tendência negativa 3 dias | Diretor (dashboard) | 72h | Gerente executa |
| 🔵 **Baixo** | Oportunidade de melhoria | Relatório semanal | 7 dias | Equipe executa |

### 14.2 Protocolo de Crise (CEO Rule Violada)

```
HORA 0: Frank AI detecta violação
  → Alerta WhatsApp CEO: "🔴 [UNIDADE] CMV: 32.1% (limite: 30%)"
  → Alerta email Diretor responsável

HORA 0-2: CEO avalia e decide
  → Abrir plano de ação (5W2H)
  → Designar responsável
  → Definir prazo de resolução

HORA 2-24: Diagnóstico
  → Frank AI gera análise de causa-raiz
  → Responsável visita unidade (se crítico)
  → Primeiras ações implementadas

DIA 2-7: Execução do plano
  → Check diário pelo Frank AI
  → Relatório de progresso (D+3 e D+7)

DIA 30: Review de fechamento
  → Meta atingida? → Plano concluído
  → Meta não atingida? → Escalada para CEO + novo plano
```

### 14.3 Controles Preventivos (Antes da Crise)

| Controle | Frequência | Mecanismo |
|---------|------------|-----------|
| Inventário surpresa | 2x/semana (rotativo) | Frank AI agenda + COO visita |
| Temperatura dos equipamentos | 3x/dia | Sensor + registro manual backup |
| Auditoria de caixa | Semanal | CFO Frank analisa fechamentos |
| Mystery shopper | Mensal | Avaliador externo + formulário |
| Análise de ficha técnica vs. CMV | Mensal | Supply + CFO Frank |
| Backup de dados ERP | Diário | Automático (retenção 90 dias) |

### 14.4 Ciclo de Aprendizado Organizacional

```
PROBLEMA → DIAGNÓSTICO → AÇÃO CORRETIVA → RESULTADO → LIÇÃO APRENDIDA
                                                              ↓
                                                    Atualização do SOP
                                                              ↓
                                                    Treinamento da equipe
                                                              ↓
                                                    Prevenção recorrência
```

**Registro no Frank AI Memory:**
- Toda ação corretiva gera uma `InsightHistory`
- `DecisionLog` registra o veredito + confiança + tokens usados
- Frank AI aprende padrões (ex: "DVR-SP-004 tem CMV elevado em dezembro historicamente")
- Insights são reaproveitados no próximo briefing e nas previsões

---

*Sistema de Gestão Davvero Gelato · Frank AI OS v1.0 · CEO Orchestrator*  
*Última atualização: 2026-04-24 · MIT © 2026 Davvero Gelato Franchising*
