# =============================================================================
# INTEGRATIONS/SHEETS.PY — Frank AI OS
# Conector Google Sheets (leitura e escrita de planilhas DRE/KPI)
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from config import SHEETS_CREDENTIALS, SHEETS_DRE_ID, SHEETS_KPI_ID

logger = logging.getLogger("frank.sheets")


class SheetsConnector:
    """
    Conector Google Sheets para leitura/escrita de DRE e KPIs.
    Usa gspread com service account.
    """

    def __init__(self):
        self._gc = None
        self._initialized = False

    def _init(self):
        """Inicializa cliente gspread (lazy init)."""
        if self._initialized:
            return
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(SHEETS_CREDENTIALS, scopes=scopes)
            self._gc = gspread.authorize(creds)
            self._initialized = True
        except FileNotFoundError:
            logger.warning(f"Credenciais Google não encontradas: {SHEETS_CREDENTIALS} — mock mode")
        except Exception as e:
            logger.warning(f"Google Sheets init error: {e} — mock mode")

    # -------------------------------------------------------------------------
    # LEITURA
    # -------------------------------------------------------------------------

    async def read_dre(self, unit_code: str, months: int = 6) -> List[Dict]:
        """
        Lê DRE da planilha para uma unidade.
        Espera aba com nome = unit_code (ex: DVR-SP-001)
        """
        self._init()
        if not self._gc:
            return self._mock_dre(unit_code, months)

        try:
            sh = self._gc.open_by_key(SHEETS_DRE_ID)
            ws = sh.worksheet(unit_code)
            records = ws.get_all_records()
            return records[-months:] if len(records) >= months else records
        except Exception as e:
            logger.warning(f"Sheets read DRE error ({unit_code}): {e}")
            return self._mock_dre(unit_code, months)

    async def read_kpis(self, unit_code: str, days: int = 30) -> List[Dict]:
        """Lê KPIs diários de uma unidade."""
        self._init()
        if not self._gc:
            return self._mock_kpis(unit_code, days)

        try:
            sh = self._gc.open_by_key(SHEETS_KPI_ID)
            ws = sh.worksheet(unit_code)
            records = ws.get_all_records()
            return records[-days:] if len(records) >= days else records
        except Exception as e:
            logger.warning(f"Sheets read KPIs error ({unit_code}): {e}")
            return self._mock_kpis(unit_code, days)

    async def read_all_units_summary(self) -> List[Dict]:
        """Lê aba de consolidação com todas as unidades."""
        self._init()
        if not self._gc:
            return self._mock_network_summary()
        try:
            sh = self._gc.open_by_key(SHEETS_DRE_ID)
            ws = sh.worksheet("REDE")
            return ws.get_all_records()
        except Exception as e:
            logger.warning(f"Sheets network summary error: {e}")
            return self._mock_network_summary()

    # -------------------------------------------------------------------------
    # ESCRITA
    # -------------------------------------------------------------------------

    async def write_kpi_row(self, unit_code: str, row: Dict) -> bool:
        """Escreve uma linha de KPI diário na planilha."""
        self._init()
        if not self._gc:
            logger.info(f"[MOCK] Escrevendo KPI em Sheets: {unit_code} — {row}")
            return True
        try:
            sh = self._gc.open_by_key(SHEETS_KPI_ID)
            ws = sh.worksheet(unit_code)
            values = list(row.values())
            ws.append_row(values)
            return True
        except Exception as e:
            logger.error(f"Sheets write error ({unit_code}): {e}")
            return False

    async def update_dre_row(self, unit_code: str, month: str, data: Dict) -> bool:
        """Atualiza linha de DRE mensal."""
        self._init()
        if not self._gc:
            logger.info(f"[MOCK] Atualizando DRE em Sheets: {unit_code} {month}")
            return True
        try:
            sh = self._gc.open_by_key(SHEETS_DRE_ID)
            ws = sh.worksheet(unit_code)
            # Busca célula pelo mês
            cell = ws.find(month)
            if cell:
                for i, (key, val) in enumerate(data.items()):
                    ws.update_cell(cell.row, cell.col + i + 1, val)
            else:
                ws.append_row([month] + list(data.values()))
            return True
        except Exception as e:
            logger.error(f"Sheets update DRE error: {e}")
            return False

    # -------------------------------------------------------------------------
    # MOCK DATA
    # -------------------------------------------------------------------------

    def _mock_dre(self, unit_code: str, months: int) -> List[Dict]:
        import random
        results = []
        for i in range(months, 0, -1):
            revenue = random.uniform(70000, 120000)
            cogs = revenue * random.uniform(0.25, 0.29)
            results.append({
                "mes": f"2025-{str(13 - i).zfill(2)}-01",
                "faturamento_bruto": round(revenue, 2),
                "cmv": round(cogs, 2),
                "cmv_pct": round(cogs / revenue * 100, 2),
                "margem_bruta": round((revenue - cogs) / revenue * 100, 2),
                "ebitda": round(revenue * random.uniform(0.12, 0.22), 2),
                "source": "mock",
            })
        return results

    def _mock_kpis(self, unit_code: str, days: int) -> List[Dict]:
        import random
        from datetime import datetime, timedelta
        results = []
        for i in range(days, 0, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            results.append({
                "data": d,
                "faturamento": round(random.uniform(800, 3200), 2),
                "transacoes": random.randint(28, 95),
                "ticket_medio": round(random.uniform(29, 48), 2),
                "nps": random.randint(55, 85),
                "source": "mock",
            })
        return results

    def _mock_network_summary(self) -> List[Dict]:
        units = ["DVR-SP-001", "DVR-SP-002", "DVR-SP-003", "DVR-SP-004", "DVR-SP-005"]
        import random
        return [
            {
                "codigo": u,
                "faturamento": round(random.uniform(60000, 130000), 2),
                "cmv_pct": round(random.uniform(24.5, 29.5), 2),
                "ticket_medio": round(random.uniform(30, 42), 2),
                "nps": random.randint(55, 82),
                "source": "mock",
            }
            for u in units
        ]
