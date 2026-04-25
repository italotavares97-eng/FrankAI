# =============================================================================
# INTEGRATIONS/CRM.PY — Frank AI OS
# Conector CRM — HubSpot / RD Station / Sults CRM
# =============================================================================

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("frank.crm")

# Suporta HubSpot ou RD Station via variável de ambiente
import os
CRM_PROVIDER   = os.getenv("CRM_PROVIDER", "hubspot")   # hubspot | rdstation | sults
HUBSPOT_TOKEN  = os.getenv("HUBSPOT_TOKEN", "")
RDSTATION_TOKEN= os.getenv("RDSTATION_TOKEN", "")
CRM_BASE_URL   = {
    "hubspot":   "https://api.hubapi.com",
    "rdstation": "https://api.rd.services",
    "sults":     os.getenv("ERP_SULTS_URL", "https://api.sults.com.br/v1"),
}


class CRMConnector:
    """
    Conector CRM unificado.
    Abstrai HubSpot, RD Station e Sults CRM numa interface comum.
    """

    def __init__(self):
        token = HUBSPOT_TOKEN if CRM_PROVIDER == "hubspot" else RDSTATION_TOKEN
        self.provider = CRM_PROVIDER
        self.client = httpx.AsyncClient(
            base_url=CRM_BASE_URL.get(CRM_PROVIDER, "https://api.hubapi.com"),
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=30,
        )

    # =========================================================================
    # LEADS / CONTATOS
    # =========================================================================

    async def get_leads(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Busca leads do CRM.
        status: "new" | "qualified" | "proposal" | "closed_won" | "closed_lost"
        """
        if not (HUBSPOT_TOKEN or RDSTATION_TOKEN):
            return self._mock_leads(limit)

        try:
            if self.provider == "hubspot":
                return await self._hubspot_get_contacts(status, limit)
            elif self.provider == "rdstation":
                return await self._rdstation_get_leads(status, limit)
        except Exception as e:
            logger.warning(f"CRM get_leads error: {e}")

        return self._mock_leads(limit)

    async def create_lead(self, data: Dict) -> Dict:
        """
        Cria novo lead/contato no CRM.
        data: {"name", "email", "phone", "city", "source", "capital_disponivel"}
        """
        if not (HUBSPOT_TOKEN or RDSTATION_TOKEN):
            logger.info(f"[MOCK CRM] Criando lead: {data.get('name')} — {data.get('email')}")
            return {"id": "mock_lead_001", "status": "created", "mock": True}

        try:
            if self.provider == "hubspot":
                return await self._hubspot_create_contact(data)
        except Exception as e:
            logger.error(f"CRM create_lead error: {e}")
        return {"error": "CRM indisponível"}

    async def update_lead_stage(self, lead_id: str, stage: str) -> bool:
        """Atualiza estágio do lead no pipeline."""
        if not (HUBSPOT_TOKEN or RDSTATION_TOKEN):
            logger.info(f"[MOCK CRM] Update lead {lead_id} → {stage}")
            return True
        try:
            if self.provider == "hubspot":
                resp = await self.client.patch(
                    f"/crm/v3/objects/contacts/{lead_id}",
                    json={"properties": {"dealstage": stage}},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"CRM update_lead_stage error: {e}")
        return False

    async def get_pipeline_summary(self) -> Dict:
        """Retorna resumo do pipeline de vendas."""
        leads = await self.get_leads()
        if not leads:
            return self._mock_pipeline_summary()

        stages = {}
        for lead in leads:
            stage = lead.get("stage", "unknown")
            stages[stage] = stages.get(stage, 0) + 1

        return {
            "total_leads": len(leads),
            "by_stage":    stages,
            "generated_at": datetime.now().isoformat(),
        }

    # =========================================================================
    # DEALS / OPORTUNIDADES
    # =========================================================================

    async def get_deals(self, stage: Optional[str] = None) -> List[Dict]:
        """Busca deals/oportunidades abertas."""
        if not (HUBSPOT_TOKEN or RDSTATION_TOKEN):
            return self._mock_deals()

        try:
            if self.provider == "hubspot":
                params = {"limit": 50}
                if stage:
                    params["properties"] = "dealstage,dealname,amount,closedate"
                resp = await self.client.get("/crm/v3/objects/deals", params=params)
                resp.raise_for_status()
                return resp.json().get("results", [])
        except Exception as e:
            logger.warning(f"CRM get_deals error: {e}")

        return self._mock_deals()

    async def create_deal(
        self,
        name: str,
        contact_id: str,
        amount: float,
        stage: str = "appointmentscheduled",
        close_date: Optional[date] = None,
    ) -> Dict:
        """Cria deal no CRM."""
        if not (HUBSPOT_TOKEN or RDSTATION_TOKEN):
            logger.info(f"[MOCK CRM] Criando deal: {name} — R${amount:,.2f}")
            return {"id": "mock_deal_001", "name": name, "mock": True}

        try:
            payload = {
                "properties": {
                    "dealname":  name,
                    "amount":    str(amount),
                    "dealstage": stage,
                    "closedate": close_date.isoformat() if close_date else None,
                },
                "associations": [
                    {"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]}
                ],
            }
            resp = await self.client.post("/crm/v3/objects/deals", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"CRM create_deal error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # HUBSPOT INTERNOS
    # =========================================================================

    async def _hubspot_get_contacts(self, status: Optional[str], limit: int) -> List[Dict]:
        params = {"limit": limit, "properties": "firstname,lastname,email,phone,city,lifecyclestage,hs_lead_status"}
        resp = await self.client.get("/crm/v3/objects/contacts", params=params)
        resp.raise_for_status()
        contacts = resp.json().get("results", [])
        normalized = []
        for c in contacts:
            props = c.get("properties", {})
            normalized.append({
                "id":     c["id"],
                "name":   f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "email":  props.get("email", ""),
                "phone":  props.get("phone", ""),
                "city":   props.get("city", ""),
                "stage":  props.get("lifecyclestage", ""),
                "source": "hubspot",
            })
        return normalized

    async def _hubspot_create_contact(self, data: Dict) -> Dict:
        name_parts = data.get("name", "").split(" ", 1)
        payload = {
            "properties": {
                "firstname":      name_parts[0],
                "lastname":       name_parts[1] if len(name_parts) > 1 else "",
                "email":          data.get("email", ""),
                "phone":          data.get("phone", ""),
                "city":           data.get("city", ""),
                "lifecyclestage": "lead",
                "hs_lead_source": data.get("source", "Frank AI OS"),
            }
        }
        resp = await self.client.post("/crm/v3/objects/contacts", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _rdstation_get_leads(self, status: Optional[str], limit: int) -> List[Dict]:
        resp = await self.client.get("/platform/contacts", params={"page_size": limit})
        resp.raise_for_status()
        return resp.json().get("contacts", [])

    # =========================================================================
    # MOCK DATA
    # =========================================================================

    def _mock_leads(self, limit: int = 10) -> List[Dict]:
        import random
        stages = ["novo", "qualificado", "reuniao", "proposta", "contrato"]
        cities = ["São Paulo", "Campinas", "Curitiba", "Belo Horizonte", "Porto Alegre", "Florianópolis"]
        return [
            {
                "id":      f"lead_{i:03d}",
                "name":    f"Prospecto {i}",
                "email":   f"prospecto{i}@email.com",
                "city":    random.choice(cities),
                "stage":   random.choice(stages),
                "capital": random.randint(180, 500) * 1000,
                "source":  random.choice(["google", "indicação", "linkedin", "abf"]),
                "mock":    True,
            }
            for i in range(1, min(limit + 1, 16))
        ]

    def _mock_deals(self) -> List[Dict]:
        return [
            {"id": "deal_001", "name": "Franquia Campinas - Shopping", "amount": 280000, "stage": "proposta", "mock": True},
            {"id": "deal_002", "name": "Franquia Curitiba - Rua", "amount": 220000, "stage": "reuniao", "mock": True},
            {"id": "deal_003", "name": "Franquia BH - Quiosque", "amount": 180000, "stage": "qualificado", "mock": True},
        ]

    def _mock_pipeline_summary(self) -> Dict:
        return {
            "total_leads": 47,
            "by_stage": {"novo": 12, "qualificado": 15, "reuniao": 9, "proposta": 7, "contrato": 4},
            "generated_at": datetime.now().isoformat(),
            "mock": True,
        }

    async def close(self):
        await self.client.aclose()
