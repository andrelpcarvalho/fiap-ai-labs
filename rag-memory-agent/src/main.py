# Para executar a função assíncrona run_lab_async
import asyncio
# Configuração de nível e formato dos logs
import logging

# Carrega variáveis do .env (GOOGLE_CLOUD_PROJECT, etc.) antes de importar o resto
from dotenv import load_dotenv

load_dotenv(override=True)

# Agente orquestrador (usa session e memory gateways)
from src.agent_router import StatefulFinanceAgent
# Gateway da Memória de Longo Prazo
from src.memory_gateway import LongTermMemoryGateway
# Gateway de sessão (Short-Term Memory / checkpoint)
from src.session_gateway import NegotiationSessionGateway
# Cálculo de custo e relatório FinOps
from src.telemetry import FinOpsTelemetry

# Define que logs INFO e superiores apareçam no formato "LEVEL - mensagem"
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


# Demonstração assíncrona: 3 turnos de mensagens, recuperação de checkpoint e relatório de economia
async def run_lab_async() -> None:
    print("=" * 60)
    print("Agente 3: The Memory - Demonstracao FSM e FinOps")
    print("=" * 60)

    # ID fixo para a demonstração (permite reutilizar mesma sessão entre turnos)
    session_id = "sessao_premium_998877"

    # Cria gateways e agente (sem Vertex configurado = mocks em memória)
    session_gw = NegotiationSessionGateway()
    memory_gw = LongTermMemoryGateway()
    agent = StatefulFinanceAgent(session_gw=session_gw, memory_gw=memory_gw)
    telemetry = FinOpsTelemetry()

    # Três mensagens simulando cliente: pedido, recusa da taxa, nova recusa
    messages = [
        "Olá, gostaria de financiar um SUV elétrico de R$ 350.000.",
        "A taxa que vocês ofereceram ontem está muito alta. Não aceito 1.49%.",
        "Ainda acho alto. Não vou fechar o financiamento assim.",
    ]

    print(f"\n[SISTEMA] Iniciando recuperacao de Checkpoint (Sessao: {session_id})...")

    total_cost = 0.0
    for i, msg in enumerate(messages, 1):
        print(f"\n[Turno {i}]")
        print(f"Cliente: {msg}")

        # Processa mensagem: recupera estado, monta prompt, chama LLM, salva checkpoint
        response_text = await agent.process_message(
            session_id=session_id,
            customer_message=msg,
            customer_tier="premium",
        )

        print(f"Agente: {response_text}")
        cost = telemetry.calculate_stateful_cost(msg, response_text)
        total_cost += cost

    print("\n")
    telemetry.print_savings_report(total_cost)


# Ponto de entrada síncrono: roda o loop de eventos com run_lab_async
def run_lab() -> None:
    asyncio.run(run_lab_async())


# Quando o script é executado diretamente (python -m src.main ou python src/main.py)
if __name__ == "__main__":
    run_lab()
