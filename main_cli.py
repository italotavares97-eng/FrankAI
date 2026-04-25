# =============================================================================
# MAIN_CLI.PY — Frank AI OS · CEO CLI Mode
# Interface de linha de comando para uso direto (sem Docker)
# =============================================================================
# Uso: python main_cli.py
# =============================================================================

from core.router import Router
from core.executor import Executor

class CEO:
    """
    CEO Agent — orquestrador de linha de comando.
    Usa o Router para rotear para o setor correto,
    e o Executor para executar ações geradas.
    """

    def __init__(self):
        self.router   = Router()
        self.executor = Executor()
        self._print_banner()

    def _print_banner(self):
        print("""
╔══════════════════════════════════════════════════════════╗
║          🍦  FRANK AI OS — Davvero Gelato  🍦            ║
║          Sistema Operacional de IA · v2.0                ║
║          CEO Agent · 8 Diretores · 38+ Agentes           ║
╚══════════════════════════════════════════════════════════╝
""")

    def handle(self, query: str) -> str:
        """Processa uma consulta e retorna a resposta."""
        print("\n🧠 Frank AI OS analisando...\n")

        # Roteia para o setor correto
        sector = self.router.route_sync(query)
        print(f"📍 Roteado para: {sector.__class__.__name__}\n")

        # Processa no setor
        response = sector.process(query)

        # Executa ações automáticas geradas
        if response.get("actions"):
            print(f"\n⚡ Executando {len(response['actions'])} ações automáticas...")
            self.executor.execute(response["actions"])

        return response["data"].get("analysis", str(response["data"]))


if __name__ == "__main__":
    ceo = CEO()

    print("Digite 'sair' para encerrar | 'ajuda' para exemplos de consultas\n")

    HELP_EXAMPLES = [
        "Como está o CMV da rede este mês?",
        "Qual a situação operacional das lojas?",
        "Crie uma campanha de verão para o Instagram",
        "Análise de expansão para Campinas",
        "Estoque crítico de algum produto?",
        "Como está o NPS geral da rede?",
        "Forecast de receita para os próximos 3 meses",
        "Revisão de contratos de franquia vencendo",
    ]

    while True:
        try:
            q = input("\n💬 Você: ").strip()

            if not q:
                continue

            if q.lower() == "sair":
                print("\n👋 Frank AI OS encerrado. Até logo!\n")
                break

            if q.lower() == "ajuda":
                print("\n📚 EXEMPLOS DE CONSULTAS:\n")
                for i, ex in enumerate(HELP_EXAMPLES, 1):
                    print(f"  {i}. {ex}")
                continue

            result = ceo.handle(q)
            print("\n" + "="*60)
            print("📊 RESPOSTA DO FRANK AI OS:")
            print("="*60)
            print(result)
            print("="*60)

        except KeyboardInterrupt:
            print("\n\n👋 Frank AI OS encerrado.\n")
            break
        except Exception as e:
            print(f"\n⚠️  Erro: {e}")
