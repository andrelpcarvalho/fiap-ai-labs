# Execução assíncrona (evita bloquear o event loop em chamadas de I/O)
import asyncio
# Logs para diagnóstico de falhas e comportamento em produção
import logging
# Acesso a variáveis de ambiente (projeto, região, flags)
import os
# Geração de IDs únicos para eventos no append_event
import uuid
from typing import Any

# Eventos e ações do Google ADK para persistir estado na sessão
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
# Serviço de sessões do Vertex AI (checkpoint de Short-Term Memory)
from google.adk.sessions import VertexAiSessionService
# Retry com backoff exponencial para falhas transitórias (rede, throttling)
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

# Exceções customizadas para tratamento específico (OCC, recuperação de sessão)
from src.exceptions import ConcurrentWriteError, SessionRecoveryError
# Modelo Pydantic do estado da negociação (FSM)
from src.state_models import NegotiationState

# Logger do módulo (aparece como "src.session_gateway" nos logs)
logger = logging.getLogger(__name__)

# Identificadores usados na API de sessões do ADK (agrupam sessões por app e usuário)
APP_NAME = "agente-3-the-memory"
USER_ID = "default"

# Política de retentativas: até 3 tentativas, espera exponencial entre 2s e 10s
# Re-tenta em qualquer exceção; após esgotar, re-lança a exceção (reraise=True)
RETRY_POLICY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)


# Extrai só o estado de negociação do objeto session, ignorando metadados do ADK
def _session_state_only(session: Any) -> dict:
    """Extrai apenas o state de sessão (sem prefixos app:, user:, temp:)."""
    # state pode não existir em sessões novas
    state = getattr(session, "state", None) or {}
    # Filtra chaves que são do app (app:, user:, temp:) para não poluir o NegotiationState
    return {
        k: v
        for k, v in state.items()
        if not k.startswith(("app:", "user:", "temp:"))
    }


# Gateway que abstrai checkpoint (Short-Term Memory): recuperar/criar sessão e salvar estado
# Usa Vertex Session Service ou mock em memória; aplica retry e OCC
class NegotiationSessionGateway:
    """
    Abstração Resiliente para Checkpointing e Short-Term Memory.
    Protege a aplicação se a conexão com o Vertex Session Service falhar, e
    garante a validação do estado usando Pydantic.
    Suporta retry com Exponential Backoff e OCC (Optimistic Concurrency Control).
    Compatível com a API do Google ADK (get_session/create_session com app_name, user_id; append_event para persistir state).
    """

    # Inicializa com project_id e location (ou lê de env); decide se usa Vertex ou mock
    def __init__(self, project_id: str | None = None, location: str | None = None):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GOOGLE_CLOUD_REGION")
        # Flag para ativar sessão persistida no Vertex (1 ou true)
        use_vertex_session = os.environ.get("USE_VERTEX_SESSION", "").strip().lower() in ("1", "true")

        # Mock se não tiver projeto configurado ou se Vertex session estiver desligado
        self.is_mock = not (bool(self.project_id) and use_vertex_session)
        if self.is_mock:
            from google.adk.sessions import InMemorySessionService

            self.service = InMemorySessionService()
            if self.project_id:
                logger.warning(
                    "Sessao em memoria (USE_VERTEX_SESSION nao ativo). Vertex AI apenas para o modelo LLM."
                )
            else:
                logger.warning("GOOGLE_CLOUD_PROJECT nao definido. Usando Session Gateway mock em memoria.")
        else:
            self.service = VertexAiSessionService(self.project_id, self.location)

    # Lógica síncrona com retry; usada via asyncio.to_thread no mock para não bloquear
    @retry(**RETRY_POLICY)
    def _recover_or_create_sync(self, session_id: str, tier: str) -> tuple[Any, NegotiationState]:
        """Lógica síncrona com retry; chamada via asyncio.to_thread a partir de recover_or_create."""
        try:
            session = self.service.get_session_sync(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session_id,
            )
        except Exception as e:
            raise SessionRecoveryError(f"Falha ao recuperar Checkpoint ADK para {session_id}: {str(e)}") from e

        # Sessão não existe: criar nova com estado inicial
        if session is None:
            state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)
            try:
                session = self.service.create_session_sync(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id,
                    state=state.model_dump(),
                )
            except Exception as e:
                raise SessionRecoveryError(f"Falha ao criar sessão ADK para {session_id}: {str(e)}") from e
            return session, state

        # Sessão existe: extrair state e validar com Pydantic
        session_state = _session_state_only(session)
        if not session_state:
            state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)
        else:
            try:
                state = NegotiationState(**session_state)
            except Exception as e:
                logger.error("Checkpoint corrompido! Resetando. Erro: %s", e)
                state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)

        return session, state

    # Recupera sessão (ou cria) de forma assíncrona; com retry em falhas de rede
    async def recover_or_create(self, session_id: str, tier: str = "standard") -> tuple[Any, NegotiationState]:
        """Recupera sessão (ou cria) de forma não bloqueante, com retry em caso de falha de rede."""
        if self.is_mock:
            return await asyncio.to_thread(self._recover_or_create_sync, session_id, tier)
        # Vertex: API é assíncrona
        try:
            session = await self.service.get_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=session_id
            )
        except Exception as e:
            raise SessionRecoveryError(f"Falha ao recuperar Checkpoint ADK para {session_id}: {str(e)}") from e
        if session is None:
            state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)
            session = await self.service.create_session(
                app_name=APP_NAME, user_id=USER_ID, state=state.model_dump()
            )
            return session, state
        session_state = _session_state_only(session)
        if not session_state:
            state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)
        else:
            try:
                state = NegotiationState(**session_state)
            except Exception as e:
                logger.error("Checkpoint corrompido! Resetando. Erro: %s", e)
                state = NegotiationState(funnel_stage="initial_contact", customer_tier=tier)
        return session, state

    # Verifica se a versão no servidor bate com a nossa; incrementa version; falha se outro writer salvou
    def _occ_check_and_bump_sync(self, session: Any, state: NegotiationState) -> None:
        """Verifica OCC e incrementa versão; falha com ConcurrentWriteError se houver conflito."""
        session_id = getattr(session, "id", None) or getattr(session, "session_id", None)
        try:
            # Busca estado atual no servidor para comparar version
            current = (
                self.service.get_session_sync(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id,
                )
                if session_id
                else session
            )
        except Exception:
            current = session
        if current is None:
            raise SessionRecoveryError(f"Sessão {session_id} não encontrada ao salvar checkpoint.")
        current_state = _session_state_only(current)
        current_version = current_state.get("version", 1)
        if current_version != state.version:
            raise ConcurrentWriteError(
                f"OCC conflict: expected version {state.version}, found {current_version}. "
                "Outro writer persistiu o checkpoint."
            )
        state.bump_version()

    # Executa OCC + bump com retry; não faz o append_event (isso fica no save_checkpoint async)
    def _save_checkpoint_sync_retry(self, session: Any, state: NegotiationState) -> None:
        """Executa OCC check e bump; o persist real é feito via append_event no save_checkpoint async."""
        # Só re-tenta se NÃO for ConcurrentWriteError (conflito não se resolve com retry)
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(lambda e: not isinstance(e, ConcurrentWriteError)),
            reraise=True,
        )
        def _do():
            self._occ_check_and_bump_sync(session, state)

        _do()

    # Salva o estado atualizado (após OCC) enviando um evento state_delta para o ADK
    async def save_checkpoint(self, session: Any, state: NegotiationState) -> None:
        """Salva a FSM atualizada (OCC) via append_event com state_delta."""
        if self.is_mock:
            try:
                await asyncio.to_thread(self._save_checkpoint_sync_retry, session, state)
            except ConcurrentWriteError:
                raise
            except Exception as e:
                logger.error("CRÍTICO: Falha ao salvar checkpoint ADK após retries. Causa: %s", e)
                raise
        else:
            session_id = getattr(session, "id", None) or getattr(session, "session_id", None)
            current = await self.service.get_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=session_id
            )
            if current is None:
                raise SessionRecoveryError(f"Sessão {session_id} não encontrada ao salvar checkpoint.")
            current_state = _session_state_only(current)
            current_version = current_state.get("version", 1)
            if current_version != state.version:
                raise ConcurrentWriteError(
                    f"OCC conflict: expected version {state.version}, found {current_version}."
                )
            state.bump_version()

        # Evento que o ADK usa para atualizar o state da sessão (state_delta = nosso NegotiationState)
        event = Event(
            author="StatefulFinanceAgent",
            invocation_id=str(uuid.uuid4()),
            actions=EventActions(state_delta=state.model_dump()),
        )
        await self.service.append_event(session=session, event=event)
