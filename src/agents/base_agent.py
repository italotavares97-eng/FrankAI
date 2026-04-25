"""Frank AI OS — Classe base para todos os agentes do sistema."""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import cache

logger = get_logger("base_agent")

# Cliente Anthropic singleton
_anthropic_client: Optional[anthropic.AsyncAnthropic] = None


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


class AgentContext:
    """Contexto compartilhado entre agentes durante uma análise."""

    def __init__(self, unit_id: Optional[str] = None, period: Optional[str] = None):
        self.unit_id = unit_id
        self.period = period or datetime.utcnow().strftime("%Y-%m-%d")
        self.network_units = settings.network_units
        self.ceo_rules = {
            "cmv_max": settings.ceo_rule_cmv_max,
            "ebitda_min": settings.ceo_rule_ebitda_min,
            "rent_max": settings.ceo_rule_rent_max,
            "payback_max": settings.ceo_rule_payback_max,
            "roi_min": settings.ceo_rule_roi_min,
        }
        self.shared_data: Dict[str, Any] = {}
        self.violations: List[Dict] = []

    def check_ceo_rules(self, metrics: Dict[str, float]) -> List[Dict]:
        """Valida métricas contra as CEO Hard Rules."""
        violations = []

        if "cmv_pct" in metrics and metrics["cmv_pct"] > self.ceo_rules["cmv_max"]:
            violations.append({
                "rule": "CMV",
                "current": metrics["cmv_pct"],
                "limit": self.ceo_rules["cmv_max"],
                "severity": "critical" if metrics["cmv_pct"] > 33 else "warning",
                "message": f"CMV {metrics['cmv_pct']:.1f}% excede limite de {self.ceo_rules['cmv_max']}%",
            })

        if "ebitda_pct" in metrics and metrics["ebitda_pct"] < self.ceo_rules["ebitda_min"]:
            violations.append({
                "rule": "EBITDA",
                "current": metrics["ebitda_pct"],
                "limit": self.ceo_rules["ebitda_min"],
                "severity": "critical" if metrics["ebitda_pct"] < 5 else "warning",
                "message": f"EBITDA {metrics['ebitda_pct']:.1f}% abaixo do mínimo de {self.ceo_rules['ebitda_min']}%",
            })

        if "rent_pct" in metrics and metrics["rent_pct"] > self.ceo_rules["rent_max"]:
            violations.append({
                "rule": "ALUGUEL",
                "current": metrics["rent_pct"],
                "limit": self.ceo_rules["rent_max"],
                "severity": "critical" if metrics["rent_pct"] > 15 else "warning",
                "message": f"Aluguel {metrics['rent_pct']:.1f}% excede limite de {self.ceo_rules['rent_max']}%",
            })

        if "payback_months" in metrics and metrics["payback_months"] > self.ceo_rules["payback_max"]:
            violations.append({
                "rule": "PAYBACK",
                "current": metrics["payback_months"],
                "limit": self.ceo_rules["payback_max"],
                "severity": "critical",
                "message": f"Payback {metrics['payback_months']:.0f}m excede limite de {self.ceo_rules['payback_max']}m",
            })

        if "roi_24m" in metrics and metrics["roi_24m"] < self.ceo_rules["roi_min"]:
            violations.append({
                "rule": "ROI 24M",
                "current": metrics["roi_24m"],
                "limit": self.ceo_rules["roi_min"],
                "severity": "critical",
                "message": f"ROI 24m {metrics['roi_24m']:.2f}x abaixo do mínimo de {self.ceo_rules['roi_min']}x",
            })

        self.violations.extend(violations)
        return violations


class BaseAgent(ABC):
    """Classe base para todos os agentes do Frank AI OS."""

    name: str = "base_agent"
    sector: str = "geral"
    description: str = "Agente base"

    def __init__(self):
        self.client = get_anthropic_client()
        self.logger = get_logger(self.name)
        self.cache = cache

    @property
    def system_prompt(self) -> str:
        """System prompt do agente — sobrescrever em subclasses."""
        return f"""Você é o agente {self.name} do Frank AI OS para a rede Davvero Gelato.
Setor: {self.sector}
Responda sempre em português brasileiro, com dados concretos e recomendações acionáveis.

CEO Hard Rules (validar SEMPRE):
- CMV ≤ 30% (crítico se > 33%)
- EBITDA ≥ 10% (crítico se < 5%)
- Aluguel/Faturamento ≤ 12%
- Payback ≤ 30 meses
- ROI 24m ≥ 1.5x

Rede: DVR-SP-001 a DVR-SP-004, DVR-RJ-001, DVR-MG-001, DVR-RS-001 (7 unidades)
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(
        self,
        messages: List[Dict],
        system: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> tuple[str, int]:
        """Chama a API Anthropic com retry automático. Retorna (texto, tokens)."""
        t0 = time.perf_counter()

        response = await self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system or self.system_prompt,
            messages=messages,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)
        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        self.logger.info(
            "llm_call",
            agent=self.name,
            tokens=tokens,
            latency_ms=latency_ms,
        )
        return text, tokens

    async def _get_cached_or_run(
        self,
        cache_key: str,
        coro,
        ttl: int = 1800,
    ) -> Any:
        """Cache-aside pattern: retorna do cache ou executa coroutine."""
        cached = await self.cache.get(cache_key)
        if cached is not None:
            self.logger.debug("cache_hit", key=cache_key)
            return cached

        result = await coro
        await self.cache.set(cache_key, result, ttl=ttl)
        return result

    @abstractmethod
    async def analyze(self, context: AgentContext, **kwargs) -> Dict[str, Any]:
        """Executa a análise principal do agente. Implementar em subclasses."""
        ...

    async def run(self, context: Optional[AgentContext] = None, **kwargs) -> Dict[str, Any]:
        """Ponto de entrada público — wrapper com logging e tratamento de erros."""
        if context is None:
            context = AgentContext()

        self.logger.info("agent_start", agent=self.name, unit=context.unit_id)
        t0 = time.perf_counter()

        try:
            result = await self.analyze(context, **kwargs)
            result["agent"] = self.name
            result["sector"] = self.sector
            result["timestamp"] = datetime.utcnow().isoformat()
            result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            result["ceo_rule_violations"] = context.violations

            self.logger.info(
                "agent_success",
                agent=self.name,
                violations=len(context.violations),
                latency_ms=result["latency_ms"],
            )
            return result

        except Exception as e:
            self.logger.error("agent_error", agent=self.name, error=str(e), exc_info=True)
            return {
                "agent": self.name,
                "sector": self.sector,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
            }


class ParallelSwarm:
    """Executa múltiplos agentes em paralelo — implementa a GOLDEN RULE."""

    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents

    async def run(
        self,
        context: Optional[AgentContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Executa todos os agentes simultaneamente com asyncio.gather()."""
        if context is None:
            context = AgentContext()

        logger.info("swarm_start", agents=[a.name for a in self.agents])
        t0 = time.perf_counter()

        # GOLDEN RULE: sempre paralelo, nunca sequencial
        results = await asyncio.gather(
            *[agent.run(context, **kwargs) for agent in self.agents],
            return_exceptions=True,
        )

        output = {}
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                output[agent.name] = {"error": str(result), "status": "error"}
            else:
                output[agent.name] = result

        output["_swarm_meta"] = {
            "agents": [a.name for a in self.agents],
            "total_latency_ms": int((time.perf_counter() - t0) * 1000),
            "all_violations": context.violations,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            "swarm_complete",
            agents=len(self.agents),
            violations=len(context.violations),
            latency_ms=output["_swarm_meta"]["total_latency_ms"],
        )

        return output
