# =============================================================================
# agent_router.py — Orquestrador do Agente com Memória (Short-Term + Long-Term)
# =============================================================================
#
# Este módulo é o "cérebro" da aplicação: coordena o fluxo entre a memória de
# curto prazo (sessão/checkpoint), a memória de longo prazo (RAG/vetorial) e o
# modelo de linguagem (Gemini). Cada mensagem do usuário passa por: recuperar
# estado da sessão → montar o prompt com contexto → chamar o LLM → atualizar
# estado (ex.: contador de recusas) → persistir checkpoint.
#
# Dependências principais:
#   - session_gateway: recuperar/criar sessão e salvar checkpoint (Short-Term Memory).
#   - memory_gateway: buscar insights do cliente no Vector Search (Long-Term Memory).
#   - state_models: modelo Pydantic do estado da negociação (FSM).
# =============================================================================

# --- Imports da biblioteca padrão e de terceiros -----------------------------

# logging: usado para registrar eventos (fluxo do agente, erros). O getLogger(__name__)
# retorna um logger cujo nome é "src.agent_router", permitindo filtrar logs por módulo.
import logging

# pathlib.Path: representação orientada a objetos de caminhos de arquivo; usado para
# apontar para o arquivo de política (memory_policy.yaml) de forma portável entre OS.
from pathlib import Path

# jinja2: motor de templates que permite variáveis ({{ funnel_stage }}, {{ proposed_rate }}, etc.)
# nos arquivos .jinja2 da pasta "prompts", gerando o system prompt dinamicamente.
import jinja2

# yaml: leitura segura de arquivos YAML (yaml.safe_load); usado para carregar
# max_rejections e outras opções do config/memory_policy.yaml.
import yaml

# --- Imports do Google ADK (Agent Development Kit) ---------------------------

# Agent (renomeado como LlmAgent): classe que representa o agente de LLM no ADK.
# Recebe nome, modelo (ex.: gemini-2.0-flash) e instruction (system prompt).
# Documentação: Google ADK.
from google.adk import Agent as LlmAgent

# Runner: executa o agente de forma assíncrona, enviando mensagens e recebendo
# eventos de resposta. Usa um session_service para manter o checkpoint alinhado
# com a sessão (Short-Term Memory).
from google.adk.runners import Runner

# types (google.genai): tipos para montar a mensagem no formato esperado pelo Gemini.
# Content = mensagem com role (user/model) e parts; Part = bloco de conteúdo (ex.: text).
from google.genai import types

# --- Imports internos do projeto ---------------------------------------------

# LongTermMemoryGateway (src/memory_gateway.py): abstração da Memória de Longo Prazo.
# Método principal: search_customer_insights(query) — busca no Vector Search (ou mock)
# e retorna texto com insights do cliente para injetar no prompt (RAG).
from src.memory_gateway import LongTermMemoryGateway

# NegotiationSessionGateway (src/session_gateway.py): abstração do checkpoint (Short-Term Memory).
# Métodos: recover_or_create(session_id, tier) → (session, state); save_checkpoint(session, state).
# APP_NAME e USER_ID: constantes usadas pela API de sessões do ADK (agrupam sessões por app/usuário).
from src.session_gateway import APP_NAME, USER_ID, NegotiationSessionGateway

# -----------------------------------------------------------------------------
# Logger e constante de caminho padrão
# -----------------------------------------------------------------------------

# Logger do módulo: em runtime aparece como "src.agent_router" nos logs. Use
# logger.info/debug/warning/error para rastrear o fluxo e falhas.
logger = logging.getLogger(__name__)

# Caminho padrão do arquivo de política de memória. Path é relativo ao diretório
# de trabalho do processo (geralmente a raiz do projeto). Contém max_rejections
# e outras opções de sessão/FinOps.
DEFAULT_POLICY_PATH = Path("config/memory_policy.yaml")


# -----------------------------------------------------------------------------
# Função auxiliar: carregar max_rejections da política
# -----------------------------------------------------------------------------

def _load_max_rejections(config_path: Path | None = None) -> int:
    """
    Carrega da política YAML quantas recusas do cliente são permitidas antes de
    transferir para um humano (handoff). Se o arquivo não existir ou a chave
    estiver ausente, retorna 3.

    Parâmetros:
        config_path: caminho do YAML; se None, usa DEFAULT_POLICY_PATH.

    Retorno:
        int: valor de session.max_rejections (ex.: 3).
    """
    # Usa o caminho informado ou o padrão (config/memory_policy.yaml).
    path = config_path or DEFAULT_POLICY_PATH

    # Se o arquivo não existir (ex.: em testes sem fixture), retorna valor padrão 3.
    if not path.exists():
        return 3

    # Abre o arquivo em UTF-8 e faz parse seguro do YAML (evita execução de código).
    # safe_load retorna None se o arquivo estiver vazio; por isso o "or {}".
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Navega: data["session"]["max_rejections"]. Se "session" ou "max_rejections"
    # não existirem, usa {} e 3 respectivamente.
    return (data.get("session") or {}).get("max_rejections", 3)


# -----------------------------------------------------------------------------
# Classe principal: StatefulFinanceAgent
# -----------------------------------------------------------------------------

class StatefulFinanceAgent:
    """
    Agente orquestrador que integra:
      - LLM (Gemini via Google ADK) com instrução dinâmica (template Jinja2).
      - Short-Term Memory: sessão/checkpoint via NegotiationSessionGateway.
      - Long-Term Memory: RAG via LongTermMemoryGateway (Vector Search).

    As dependências (session_gw, memory_gw) são injetadas no construtor (IoC),
    o que facilita testes com mocks e troca de implementação (ex.: outro backend de sessão).
    """

    def __init__(
        self,
        session_gw: NegotiationSessionGateway,
        memory_gw: LongTermMemoryGateway,
        *,
        policy_path: Path | None = None,
    ):
        """
        Inicializa o agente com os gateways de memória e opcionalmente o caminho
        da política. O * força policy_path a ser passado apenas por nome (keyword-only).
        """
        # Guarda referências aos gateways para uso em process_message.
        self.session_gw = session_gw
        self.memory_gw = memory_gw

        # Carrega da política (YAML) o limite de recusas antes do handoff.
        # Função definida neste arquivo (agent_router.py): _load_max_rejections.
        self._max_rejections = _load_max_rejections(policy_path)

        # Ambiente Jinja2 que carrega templates a partir da pasta "prompts" (relativa ao CWD).
        # FileSystemLoader("prompts") procura arquivos como prompts/negotiator.jinja2.
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("prompts"))

        # Referências aos templates: negotiator = system prompt do negociador;
        # injector = template que junta a mensagem do usuário com os insights da memória long-term.
        self.negotiator_template = self.jinja_env.get_template("negotiator.jinja2")
        self.injector_template = self.jinja_env.get_template("context_injector.jinja2")

        # Agente LLM do ADK: nome interno, modelo Gemini e instrução base.
        # A instrução completa é sobrescrita a cada mensagem pelo render do negotiator_template
        # (que inclui funnel_stage, proposed_rate, rejection_count, customer_tier).
        self.llm_agent = LlmAgent(
            name="StatefulAutoFinanceNegotiator",
            model="gemini-2.0-flash",
            instruction="Voce e um negociador de financiamentos. O contexto sera dinamicamente injetado.",
        )

        # Runner do ADK: executa o agente de forma assíncrona. Usa o MESMO session_service
        # que o session_gw, para que o checkpoint persistido pelo gateway e o estado
        # usado pelo chat do ADK sejam da mesma sessão (consistência Short-Term Memory).
        # APP_NAME e USER_ID vêm de src/session_gateway.py (constantes do app e usuário).
        self.runner = Runner(
            app_name=APP_NAME,
            agent=self.llm_agent,
            session_service=self.session_gw.service,
        )

    # -------------------------------------------------------------------------
    # Fluxo principal: process_message
    # -------------------------------------------------------------------------

    async def process_message(
        self,
        session_id: str,
        customer_message: str,
        customer_tier: str = "standard",
    ) -> str:
        """
        Processa uma mensagem do cliente de forma assíncrona: recupera estado,
        monta prompt (com RAG quando aplicável), chama o LLM, atualiza estado
        (ex.: incremento de recusas) e persiste o checkpoint.

        Parâmetros:
            session_id: identificador da sessão (e.g. ID do chat).
            customer_message: texto enviado pelo cliente.
            customer_tier: perfil do cliente ("standard" ou "premium"), usado na FSM e no prompt.

        Retorno:
            str: resposta do agente ao cliente. Em handoff, retorna mensagem de sistema.
        """
        # --- 1) Recuperar ou criar sessão e estado (Short-Term Memory) ---------
        #
        # recover_or_create está em src/session_gateway.py, classe NegotiationSessionGateway.
        # Faz: get_session; se não existir, create_session com estado inicial; se existir,
        # extrai o state do checkpoint e valida com NegotiationState (Pydantic).
        # Retorna: (objeto sessão ADK, NegotiationState).
        adk_session, state = await self.session_gw.recover_or_create(session_id, customer_tier)

        # --- 2) Se já está em handoff, não processar nova mensagem -------------
        #
        # state é NegotiationState (src/state_models.py): funnel_stage pode ser
        # "initial_contact" | "analyzing_credit" | "rate_proposed" | "contract_signed" | "human_handoff".
        if state.funnel_stage == "human_handoff":
            return "[SYSTEM] Negociação encerrada pelo agente. Aguarde a transferência para um especialista."

        # --- 3) Montar system prompt do negociador (Jinja2) --------------------
        #
        # negotiator_template está em prompts/negotiator.jinja2; render injeta as
        # variáveis do estado atual no texto do prompt (etapa do funil, taxa proposta, etc.).
        system_prompt = self.negotiator_template.render(
            funnel_stage=state.funnel_stage,
            proposed_rate=state.proposed_rate,
            rejection_count=state.rejection_count,
            customer_tier=state.customer_tier,
        )
        # O ADK usa a propriedade instruction do agente como system prompt.
        self.llm_agent.instruction = system_prompt

        # --- 4) Enriquecer mensagem do usuário com RAG (Long-Term Memory) -------
        #
        # Só buscamos insights nas etapas em que a proposta já foi feita ou o crédito
        # está sendo analisado; nas outras, o cliente_message segue sem alteração.
        contextual_prompt = customer_message
        if state.funnel_stage in ("rate_proposed", "analyzing_credit"):
            # Query enriquecida: session_id + contexto da mensagem (melhor recuperação semântica).
            context_snippet = (customer_message or "").strip()[:200]
            query = f"Sessao: {session_id}. Contexto do cliente: {context_snippet}" if context_snippet else f"Sessao: {session_id}"
            where_metadata = {"session_id": session_id}  # filtra insights desta sessão quando indexado com session_id
            insights = await self.memory_gw.search_customer_insights(query=query, where_metadata=where_metadata)
            if insights:
                # context_injector.jinja2 (prompts/) junta base_prompt e long_term_insights.
                contextual_prompt = self.injector_template.render(
                    base_prompt=customer_message,
                    long_term_insights=insights,
                )

        # --- 5) Montar mensagem no formato Gemini (Content + Part) --------------
        #
        # types vem de google.genai: Content(role="user", parts=[Part(text=...)])
        # é o formato esperado pelo Runner para a mensagem do usuário.
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=contextual_prompt)],
        )

        # --- 6) Executar o agente de forma assíncrona e acumular resposta -------
        #
        # run_async está no Runner do ADK (google.adk.runners). Gera eventos (async for);
        # cada evento pode conter content.parts com texto. Tomamos a última parte com
        # texto como resposta (response_text).
        response_text = ""
        async for event in self.runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=new_message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        response_text = part.text

        # --- 7) Atualizar estado: contador de recusas e possível handoff --------
        #
        # increment_rejection está em src/state_models.py, classe NegotiationState.
        # Incrementa rejection_count; se atingir _max_rejections, altera funnel_stage
        # para "human_handoff". _max_rejections foi carregado do YAML em __init__.
        state.increment_rejection(max_rejections=self._max_rejections)

        # Se entrou em handoff, o state já reflete; não é necessário ação extra aqui.
        if state.funnel_stage == "human_handoff":
            pass  # Handoff ja refletido no state

        # --- 8) Persistir estado atualizado no checkpoint (Short-Term Memory) ---
        #
        # save_checkpoint está em src/session_gateway.py, NegotiationSessionGateway.
        # Aplica OCC (versão), incrementa version no state e envia evento state_delta
        # para o session_service (append_event), persistindo o NegotiationState.
        await self.session_gw.save_checkpoint(adk_session, state)

        return response_text
