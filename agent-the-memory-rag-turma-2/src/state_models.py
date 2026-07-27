# Literal define um conjunto fixo de strings permitidas (evita valores inválidos)
from typing import Literal

# Pydantic garante validação e serialização consistente do estado (importante para checkpoint)
from pydantic import BaseModel, Field


# Modelo que representa o estado da Máquina de Estados (FSM) da negociação
# Evita que o LLM corrompa o checkpoint: só campos definidos aqui são persistidos
# O campo version é usado para OCC (Optimistic Concurrency Control) no save
class NegotiationState(BaseModel):
    """
    Modelo estrito para a Máquina de Estados (FSM) da Negociação.
    Evita corrupção do checkpoint (Short-Term Memory) pelo LLM.
    Campo `version` permite Optimistic Concurrency Control (OCC) no save.
    """

    # Etapa atual do funil de vendas (apenas um dos valores listados é válido)
    funnel_stage: Literal["initial_contact", "analyzing_credit", "rate_proposed", "contract_signed", "human_handoff"]
    # Quantas vezes o cliente recusou a proposta; usado para decidir handoff para humano
    rejection_count: int = Field(default=0, ge=0)
    # Taxa de juros proposta (None até que seja calculada e oferecida)
    proposed_rate: float | None = None
    # Perfil do cliente (impacta ofertas e regras de negociação)
    customer_tier: Literal["standard", "premium"]
    # Versão do estado: incrementada a cada save para detectar escritas concorrentes (OCC)
    version: int = Field(default=1, ge=1, description="OCC: incrementado a cada save para detectar race conditions")

    # Aumenta o contador de recusas; se atingir o máximo, muda para transferência humana
    def increment_rejection(self, max_rejections: int = 3) -> None:
        """Incrementa contador de recusa. Handoff quando atingir max_rejections (configurável via YAML)."""
        self.rejection_count += 1
        if self.rejection_count >= max_rejections:
            self.funnel_stage = "human_handoff"

    # Chamado antes de persistir: incrementa version para que a próxima leitura detecte conflitos
    def bump_version(self) -> None:
        """Incrementa versão para OCC; chamado antes de persistir."""
        self.version += 1
