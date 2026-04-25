-- =============================================================================
-- SEEDS.SQL — Frank AI OS · Davvero Gelato
-- Dados iniciais para desenvolvimento e demonstração
-- =============================================================================

SET search_path TO davvero, public;

-- =============================================================================
-- FRANQUEADOS
-- =============================================================================

INSERT INTO franchisees (id, name, email, phone, city, state, contract_start, contract_end, royalty_pct, mkt_fund_pct)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Carlos Mendes', 'carlos@dvr.com', '11999990001', 'São Paulo', 'SP', '2020-01-15', '2025-01-15', 0.085, 0.015),
  ('22222222-2222-2222-2222-222222222222', 'Ana Paula Santos', 'ana@dvr.com', '11999990002', 'São Paulo', 'SP', '2021-03-01', '2026-03-01', 0.085, 0.015),
  ('33333333-3333-3333-3333-333333333333', 'Roberto Lima', 'roberto@dvr.com', '19999990003', 'Campinas', 'SP', '2022-06-01', '2027-06-01', 0.085, 0.015),
  ('44444444-4444-4444-4444-444444444444', 'Juliana Costa', 'juliana@dvr.com', '11999990004', 'São Paulo', 'SP', '2023-01-10', '2028-01-10', 0.085, 0.015),
  ('55555555-5555-5555-5555-555555555555', 'Fernando Alves', 'fernando@dvr.com', '41999990005', 'Curitiba', 'PR', '2023-09-01', '2028-09-01', 0.085, 0.015)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- UNIDADES
-- =============================================================================

INSERT INTO units (id, franchisee_id, code, name, format, status, color_status, city, state, shopping, opening_date, initial_investment, monthly_rent, cluster, priority)
VALUES
  ('a1111111-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'DVR-SP-001', 'Davvero Villa Lobos', 'loja_pequena', 'ativo', 'verde', 'São Paulo', 'SP', 'Shopping Villa Lobos', '2020-02-01', 280000, 18000, 'Capital SP', 1),
  ('a2222222-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'DVR-SP-002', 'Davvero Morumbi', 'loja_completa', 'ativo', 'verde', 'São Paulo', 'SP', 'Shopping Morumbi', '2020-08-15', 380000, 25000, 'Capital SP', 1),
  ('a3333333-0000-0000-0000-000000000003', '22222222-2222-2222-2222-222222222222', 'DVR-SP-003', 'Davvero Ibirapuera', 'loja_pequena', 'ativo', 'amarelo', 'São Paulo', 'SP', 'Shopping Ibirapuera', '2021-04-10', 260000, 22000, 'Capital SP', 1),
  ('a4444444-0000-0000-0000-000000000004', '22222222-2222-2222-2222-222222222222', 'DVR-SP-004', 'Davvero Eldorado', 'loja_pequena', 'ativo', 'laranja', 'São Paulo', 'SP', 'Shopping Eldorado', '2021-11-20', 250000, 20000, 'Capital SP', 2),
  ('a5555555-0000-0000-0000-000000000005', '33333333-3333-3333-3333-333333333333', 'DVR-SP-005', 'Davvero Campinas', 'quiosque', 'ativo', 'verde', 'Campinas', 'SP', 'Shopping Galleria', '2022-07-01', 180000, 9500, 'Interior SP', 2),
  ('a6666666-0000-0000-0000-000000000006', '44444444-4444-4444-4444-444444444444', 'DVR-SP-006', 'Davvero Iguatemi', 'loja_pequena', 'ativo', 'verde', 'São Paulo', 'SP', 'Shopping Iguatemi', '2023-03-15', 290000, 23000, 'Capital SP', 1),
  ('a7777777-0000-0000-0000-000000000007', '55555555-5555-5555-5555-555555555555', 'DVR-PR-001', 'Davvero Curitiba', 'quiosque', 'ativo', 'amarelo', 'Curitiba', 'PR', 'Shopping Mueller', '2023-10-01', 175000, 8500, 'Sul', 2)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- FINANCEIROS — últimos 3 meses (valores realistas Davvero)
-- =============================================================================

-- Março 2026
INSERT INTO unit_financials (unit_id, month, gross_revenue, cogs_value, bonuses_received, rent, payroll, electricity, packaging, royalties, mkt_fund, maintenance, other_opex, cto_monthly, depreciation)
VALUES
  ('a1111111-0000-0000-0000-000000000001', '2026-03-01', 95000, 24225,  800, 18000, 20900, 1800, 2500, 8075, 1425, 900, 2800, 2000, 1200),
  ('a2222222-0000-0000-0000-000000000002', '2026-03-01', 128000, 33280, 1200, 25000, 28160, 2400, 3200, 10880, 1920, 1200, 3500, 3000, 1800),
  ('a3333333-0000-0000-0000-000000000003', '2026-03-01', 82000, 23780,  600, 22000, 18040, 1600, 2100, 6970,  1230, 750, 2200, 1500, 900),
  ('a4444444-0000-0000-0000-000000000004', '2026-03-01', 71000, 22010,  400, 20000, 15620, 1400, 1900, 6035,  1065, 650, 1900, 1200, 700),
  ('a5555555-0000-0000-0000-000000000005', '2026-03-01', 48000, 12720,  300,  9500, 10560,  900, 1300, 4080,   720, 400, 1300, 800,  500),
  ('a6666666-0000-0000-0000-000000000006', '2026-03-01', 105000, 26775, 900, 23000, 23100, 2000, 2700, 8925,  1575, 950, 3000, 2200, 1300),
  ('a7777777-0000-0000-0000-000000000007', '2026-03-01', 42000, 12390,  200,  8500,  9240,  800, 1100, 3570,   630, 350, 1200, 700,  400)
ON CONFLICT (unit_id, month) DO NOTHING;

-- Fevereiro 2026
INSERT INTO unit_financials (unit_id, month, gross_revenue, cogs_value, bonuses_received, rent, payroll, electricity, packaging, royalties, mkt_fund, maintenance, other_opex, cto_monthly, depreciation)
VALUES
  ('a1111111-0000-0000-0000-000000000001', '2026-02-01', 88000, 22880, 700, 18000, 19360, 1750, 2300, 7480, 1320, 850, 2600, 2000, 1200),
  ('a2222222-0000-0000-0000-000000000002', '2026-02-01', 118000, 31270, 1000, 25000, 25960, 2300, 3000, 10030, 1770, 1100, 3200, 3000, 1800),
  ('a3333333-0000-0000-0000-000000000003', '2026-02-01', 75000, 22500,  500, 22000, 16500, 1550, 1900, 6375,  1125, 700, 2000, 1500, 900),
  ('a4444444-0000-0000-0000-000000000004', '2026-02-01', 65000, 21450,  350, 20000, 14300, 1350, 1750, 5525,   975, 600, 1750, 1200, 700),
  ('a5555555-0000-0000-0000-000000000005', '2026-02-01', 44000, 11880,  250,  9500,  9680,  850, 1200, 3740,   660, 380, 1200, 800,  500),
  ('a6666666-0000-0000-0000-000000000006', '2026-02-01', 97000, 25220,  800, 23000, 21340, 1900, 2500, 8245,  1455, 900, 2800, 2200, 1300),
  ('a7777777-0000-0000-0000-000000000007', '2026-02-01', 38000, 11400,  150,  8500,  8360,  750, 1000, 3230,   570, 320, 1100, 700,  400)
ON CONFLICT (unit_id, month) DO NOTHING;

-- =============================================================================
-- KPIs DIÁRIOS — últimos 7 dias (amostra)
-- =============================================================================

INSERT INTO unit_daily_kpis (unit_id, date, gross_revenue, transactions, team_hours, stockout_count, waste_value, nps_score)
SELECT
  u.id,
  CURRENT_DATE - (s.d || ' days')::interval,
  CASE u.format
    WHEN 'loja_completa' THEN 4200 + (random() * 1200 - 600)::int
    WHEN 'loja_pequena'  THEN 3100 + (random() * 800  - 400)::int
    WHEN 'quiosque'      THEN 1600 + (random() * 400  - 200)::int
    ELSE 2000
  END,
  CASE u.format
    WHEN 'loja_completa' THEN 115 + (random() * 30 - 15)::int
    WHEN 'loja_pequena'  THEN 85  + (random() * 20 - 10)::int
    WHEN 'quiosque'      THEN 48  + (random() * 12 - 6)::int
    ELSE 60
  END,
  8.0 + (random() * 2 - 1),
  (random() * 3)::int,
  (random() * 120)::int + 20,
  65 + (random() * 25)::int
FROM units u
CROSS JOIN (SELECT generate_series(1, 7) AS d) s
WHERE u.status = 'ativo'
ON CONFLICT (unit_id, date) DO NOTHING;

-- =============================================================================
-- FORNECEDORES
-- =============================================================================

INSERT INTO suppliers (name, cnpj, category, contact_name, contact_email, score, quality_score, price_score, delivery_score, payment_terms, lead_time_days, status, is_strategic)
VALUES
  ('Laticínios Mooca',   '11.222.333/0001-44', 'lácteos',    'Marcos Souza',   'marcos@laticmooca.com.br',  88, 90, 82, 92, 30, 2, 'ativo', true),
  ('FrutiPulp Brasil',   '22.333.444/0001-55', 'frutas',     'Carla Nunes',    'carla@frutipulp.com.br',    79, 85, 75, 77, 21, 3, 'ativo', true),
  ('EmbalaPrime',        '33.444.555/0001-66', 'embalagens', 'Pedro Andrade',  'pedro@embalaprime.com.br',  85, 80, 88, 87, 45, 4, 'ativo', true),
  ('InsumosFoods',       '44.555.666/0001-77', 'insumos',    'Luiza Ferreira', 'luiza@insumofoods.com.br',  72, 78, 70, 68, 30, 5, 'ativo', false),
  ('CremosoBR',          '55.666.777/0001-88', 'lácteos',    'André Ramos',    'andre@cremoso.com.br',      65, 70, 68, 57, 21, 7, 'ativo', false)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- AUDITORIAS DE QUALIDADE
-- =============================================================================

INSERT INTO quality_audits (unit_id, audit_date, auditor_name, audit_type, score_visual, score_product, score_portioning, score_service, score_hygiene, score_operations, non_conformities, action_plan)
VALUES
  ('a1111111-0000-0000-0000-000000000001', CURRENT_DATE - 15, 'Patrícia Oliveira', 'presencial', 92, 88, 85, 90, 95, 88, '{}', 'Manter padrão atual'),
  ('a2222222-0000-0000-0000-000000000002', CURRENT_DATE - 10, 'Patrícia Oliveira', 'presencial', 95, 92, 90, 94, 96, 91, '{}', 'Excelente — manter'),
  ('a3333333-0000-0000-0000-000000000003', CURRENT_DATE - 20, 'João Carlos',       'presencial', 78, 75, 72, 80, 85, 74, '["Porcionamento irregular","Organização balcão"]', 'Treinar porcionamento esta semana'),
  ('a4444444-0000-0000-0000-000000000004', CURRENT_DATE -  5, 'João Carlos',       'surpresa',   68, 65, 60, 72, 80, 65, '["CMV elevado","Mise en place"]', 'Reunião urgente com gerente — plano de ação 7 dias'),
  ('a5555555-0000-0000-0000-000000000005', CURRENT_DATE - 25, 'Maria Helena',      'presencial', 88, 85, 82, 87, 90, 84, '{}', 'OK — próxima auditoria em 30 dias'),
  ('a6666666-0000-0000-0000-000000000006', CURRENT_DATE -  8, 'Patrícia Oliveira', 'presencial', 91, 90, 88, 92, 94, 89, '{}', 'Top performer'),
  ('a7777777-0000-0000-0000-000000000007', CURRENT_DATE - 30, 'Maria Helena',      'presencial', 82, 80, 76, 83, 88, 79, '["Estoque visível"]', 'Reorganizar área de estoque')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- LEADS B2B
-- =============================================================================

INSERT INTO leads_b2b (name, email, phone, city, state, status, available_capital, has_experience, is_operator, score, source, first_contact)
VALUES
  ('Ricardo Bittencourt', 'ricardo.b@email.com', '11999001001', 'São Paulo',       'SP', 'proposta',    350000, true,  true,  85, 'indicação', CURRENT_DATE - 45),
  ('Fernanda Guimarães',  'fernanda@email.com',  '41998002002', 'Curitiba',        'PR', 'qualificado', 280000, false, true,  72, 'linkedin',  CURRENT_DATE - 30),
  ('Thiago Monteiro',     'thiago.m@email.com',  '19997003003', 'Campinas',        'SP', 'reuniao',     400000, true,  false, 78, 'google',    CURRENT_DATE - 20),
  ('Camila Rodrigues',    'camila.r@email.com',  '51996004004', 'Porto Alegre',    'RS', 'novo',        220000, false, true,  60, 'abf',       CURRENT_DATE - 10),
  ('Marcos Tavares',      'marcos.t@email.com',  '31995005005', 'Belo Horizonte',  'MG', 'qualificado', 320000, true,  true,  80, 'indicação', CURRENT_DATE - 15),
  ('Aline Ferreira',      'aline.f@email.com',   '85994006006', 'Fortaleza',       'CE', 'novo',        250000, false, true,  55, 'instagram', CURRENT_DATE -  5)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- LIÇÕES DO FRANK (pré-carregadas)
-- =============================================================================

INSERT INTO frank_lessons (error_desc, correction, rule, example, director)
VALUES
  ('Recomendar expansão sem validar Hard Rules de ROI', 'Sempre calcular payback e ROI antes de aprovar nova unidade', 'Toda recomendação de expansão deve validar: payback ≤ 30 meses e ROI ≥ 1.5x em 24m', 'Lead em Campinas: aluguel R$12k, receita projetada R$45k → payback 28m → APROVADO', 'CSO'),
  ('Analisar CMV sem considerar bonificações de fornecedor', 'CMV real = (cogs - bonificações) / receita líquida', 'Sempre usar net_cogs (cogs - bonuses) no cálculo do CMV, não o cogs bruto', 'Loja com R$25k COGS e R$1.2k bonificação → CMV real é sobre R$23.8k', 'CFO'),
  ('Comparar ticket médio de lojas de formatos diferentes', 'Comparar ticket apenas entre lojas do mesmo formato', 'Ticket médio de quiosque ≠ loja completa — usar benchmark por formato', 'Quiosque meta: R$28 | Loja pequena meta: R$35 | Loja completa meta: R$42', 'COO'),
  ('Propor campanha sem orçamento definido', 'Toda campanha deve ter budget, canal, objetivo e KPI de sucesso definidos', 'Campanhas sem budget aprovado não devem ser recomendadas como EXECUTAR', 'Meta Ads: budget R$5k/mês | objetivo: 50 leads B2C | CPL alvo: R$100', 'CMO')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- INVENTÁRIO (estoque inicial)
-- =============================================================================

INSERT INTO inventory (unit_id, product_name, sku, category, current_qty, unit, min_qty, reorder_qty)
SELECT
  u.id,
  i.product_name, i.sku, i.category, i.qty, i.unit, i.min_qty, i.reorder_qty
FROM units u
CROSS JOIN (VALUES
  ('Leite Integral 1L',   'LT001', 'lácteos',    45.0, 'L',  30.0, 60.0),
  ('Creme de Leite 500ml','CR001', 'lácteos',    18.0, 'L',  15.0, 30.0),
  ('Açúcar Refinado',     'AC001', 'insumos',    28.0, 'kg', 20.0, 40.0),
  ('Polpa Morango 1kg',   'FR001', 'frutas',      8.0, 'kg', 10.0, 20.0),
  ('Copo 350ml',          'CP001', 'embalagens', 450.0,'un', 200.0,500.0),
  ('Copo 500ml',          'CP002', 'embalagens', 280.0,'un', 150.0,400.0),
  ('Colher Degustação',   'CL001', 'embalagens', 850.0,'un', 500.0,1000.0)
) AS i(product_name, sku, category, qty, unit, min_qty, reorder_qty)
WHERE u.status = 'ativo'
ON CONFLICT (unit_id, sku) DO NOTHING;
