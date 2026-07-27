# Para rodar busca vetorial em thread separada e não bloquear o event loop
import asyncio
import json
# Logs quando Vector Search falha ou está em modo mock
import logging
# Ler GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_REGION, VECTOR_SEARCH_ENDPOINT_ID
import os
from pathlib import Path

# Retry com backoff exponencial quando a busca vetorial falha (rede, throttling)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Exceção lançada quando o Vector Search está indisponível (permite degradação graciosa)
from src.exceptions import VectorSearchError

logger = logging.getLogger(__name__)

# Até 3 tentativas, espera exponencial 2s–10s; re-lança exceção ao final
RETRY_POLICY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)

DEFAULT_POLICY_PATH = Path("config/memory_policy.yaml")


def _load_vertex_content_store(path: Path) -> dict[str, str]:
    """Carrega content store Vertex (JSONL id, content). Última ocorrência de cada id vence."""
    out = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                out[str(row.get("id", ""))] = str(row.get("content", ""))
            except (json.JSONDecodeError, TypeError):
                continue
    return out


def _load_vector_search_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_POLICY_PATH
    if not path.exists():
        return {}
    import yaml
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return (data.get("vector_search") or {}).copy()


# Abstração da Memória de Longo Prazo (RAG)
# Backend escolhido via config: chroma | vertex | mock
class LongTermMemoryGateway:
    """
    Abstração da Memória de Longo Prazo.
    Suporta ChromaDB, Vertex AI Vector Search ou mock, conforme config/memory_policy.yaml (vector_search.backend).

    Comportamento por backend:
    - Chroma: aplica min_similarity_score (pós-busca), where_metadata e ordenação por similaridade.
    - Vertex: usa MatchingEngineIndexEndpoint.find_neighbors; aplica min_similarity_score e ordenação
      no cliente; conteúdo vindo do content store local. where_metadata não é aplicado (filtro server-side
      não usado nesta implementação).
    - Mock: ignora where_metadata e min_similarity; retorno fixo por substring na query (testes/degradação).
    """

    def __init__(
        self,
        project_id: str | None = None,
        location: str | None = None,
        index_endpoint: str | None = None,
        *,
        config_path: Path | None = None,
    ):
        vs_cfg = _load_vector_search_config(config_path)
        self._vs_cfg = vs_cfg
        backend = (vs_cfg.get("backend") or "mock").lower()
        self._backend = backend
        self._max_documents = int(vs_cfg.get("max_documents", 3))
        self._min_similarity_score = float(vs_cfg.get("min_similarity_score", 0.70))

        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION")
        self.index_endpoint = index_endpoint or os.environ.get("VECTOR_SEARCH_ENDPOINT_ID")

        self._chroma_collection = None
        self.service = None
        self.is_mock = True

        if backend == "chroma":
            chroma_cfg = vs_cfg.get("chroma") or {}
            persist_dir = chroma_cfg.get("persist_directory", "data/chroma")
            collection_name = chroma_cfg.get("collection_name", "customer_insights")
            from src.indexing.vector_store import _get_chroma_collection
            self._chroma_collection = _get_chroma_collection(persist_dir, collection_name)
            self.is_mock = False
            logger.info("Long-Term Memory: ChromaDB (%s)", persist_dir)
        elif backend == "vertex":
            self.is_mock = not bool(self.index_endpoint)
            self._vertex_endpoint = None
            self._vertex_deployed_index_id = None
            self._vertex_content_store_path = None
            if not self.is_mock:
                vertex_cfg = vs_cfg.get("vertex") or {}
                deployed_id = vertex_cfg.get("deployed_index_id") or os.environ.get("VECTOR_SEARCH_DEPLOYED_INDEX_ID")
                content_store = vertex_cfg.get("content_store_path") or str(Path("data") / "vertex_content_store.jsonl")
                try:
                    from google.cloud import aiplatform
                    if self.index_endpoint.startswith("projects/"):
                        endpoint_name = self.index_endpoint
                    else:
                        endpoint_name = f"projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.index_endpoint}"
                    self._vertex_endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_name)
                    self._vertex_deployed_index_id = deployed_id or self.index_endpoint
                    self._vertex_content_store_path = Path(content_store)
                    logger.info("Long-Term Memory: Vertex AI Vector Search (find_neighbors)")
                except Exception as e:
                    logger.warning("Vertex endpoint não inicializado: %s. Usando mock.", e)
                    self.is_mock = True
            if self.is_mock:
                logger.warning("Vertex configurado mas VECTOR_SEARCH_ENDPOINT_ID ausente. Usando mock.")
        else:
            logger.warning("Long-Term Memory: Mock de Banco Vetorial.")

    def _search_customer_insights_sync(self, query: str, where_metadata: dict | None = None) -> str:
        """Lógica síncrona com retry; chamada via asyncio.to_thread."""
        if self._backend == "chroma" and self._chroma_collection is not None:
            try:
                try:
                    n = self._chroma_collection.count()
                except Exception:
                    n = 0
                if n == 0:
                    return ""
                from src.indexing.embedding import embed_texts
                query_embeddings = embed_texts([query], for_query=True)
                if not query_embeddings:
                    return ""
                kwargs = {
                    "query_embeddings": query_embeddings,
                    "n_results": self._max_documents,
                    "include": ["documents", "distances"],
                }
                if where_metadata:
                    kwargs["where"] = where_metadata
                results = self._chroma_collection.query(**kwargs)
                docs = results.get("documents") or []
                dists = results.get("distances") or []
                if not isinstance(docs, (list, tuple)) or not isinstance(dists, (list, tuple)):
                    return ""
                if not docs:
                    return ""
                first_docs = docs[0]
                if first_docs is None or (hasattr(first_docs, "__len__") and not isinstance(first_docs, (str, dict)) and len(first_docs) == 0):
                    return ""
                doc_list = list(first_docs) if isinstance(first_docs, (list, tuple)) else [first_docs]
                if not doc_list:
                    return ""
                # Chroma cosine: menor distância = mais similar; similaridade = max(0, 1 - distance)
                dist_list = [0.0] * len(doc_list)
                if dists and isinstance(dists, (list, tuple)) and len(dists) > 0:
                    d0 = dists[0]
                    if isinstance(d0, (list, tuple)):
                        dist_list = list(d0)[: len(doc_list)]
                    elif hasattr(d0, "__iter__") and not isinstance(d0, (str, dict)):
                        dist_list = list(d0)[: len(doc_list)]
                scored = []
                for doc, dist in zip(doc_list, dist_list):
                    sim = max(0.0, 1.0 - float(dist))
                    if sim >= self._min_similarity_score and doc:
                        scored.append((sim, doc))
                scored.sort(key=lambda x: -x[0])
                return " ".join(d[1] for d in scored)
            except Exception as e:
                logger.error("Falha na busca Chroma. Erro: %s", e)
                raise VectorSearchError(str(e)) from e

        if self._backend == "vertex" and self._vertex_endpoint is not None and self._vertex_content_store_path is not None:
            try:
                from src.indexing.embedding import embed_texts
                query_embeddings = embed_texts([query], for_query=True)
                if not query_embeddings:
                    return ""
                queries = [query_embeddings[0]]
                response = self._vertex_endpoint.find_neighbors(
                    deployed_index_id=self._vertex_deployed_index_id,
                    queries=queries,
                    num_neighbors=self._max_documents,
                )
                if not response or not response[0]:
                    return ""
                id_to_content = _load_vertex_content_store(self._vertex_content_store_path)
                scored = []
                for neighbor in response[0]:
                    datapoint_id = getattr(neighbor, "datapoint_id", None) or getattr(neighbor, "id", None)
                    distance = float(getattr(neighbor, "distance", 1.0))
                    if datapoint_id is None:
                        continue
                    sim = max(0.0, 1.0 - distance)
                    if sim >= self._min_similarity_score:
                        content = id_to_content.get(str(datapoint_id), "")
                        if content:
                            scored.append((sim, content))
                scored.sort(key=lambda x: -x[0])
                return " ".join(c for _, c in scored[: self._max_documents])
            except Exception as e:
                logger.error("Falha na consulta Vetorial. Degrading gracefully... Erro: %s", e)
                raise VectorSearchError(str(e)) from e

        if self._backend == "mock" or self.is_mock:
            if "sessao_premium" in query:
                return "O cliente é conservador, negocia as taxas com agressividade e só fecha com taxas < 1.0%."
            return "Nenhum histórico prévio encontrado para este CPF."

        return ""

    @retry(**RETRY_POLICY)
    def _search_customer_insights_sync_retry(self, query: str, where_metadata: dict | None = None) -> str:
        """Busca com retry; após esgotar retries, o caller pode degradar (retornar '')."""
        return self._search_customer_insights_sync(query, where_metadata=where_metadata)

    async def search_customer_insights(
        self,
        query: str,
        *,
        where_metadata: dict | None = None,
    ) -> str:
        """
        Busca conhecimento do cliente (RAG context). Não bloqueia o event loop.
        Em falha persistente após retries, retorna string vazia (graceful degradation).

        where_metadata: filtro opcional; aplicado apenas em backend Chroma (Vertex e mock ignoram).
        Quando where retorna 0 resultados, retorna "" (sem fallback automático).
        """
        try:
            return await asyncio.to_thread(
                self._search_customer_insights_sync_retry,
                query,
                where_metadata,
            )
        except Exception:
            logger.warning("Long-Term Memory indisponível após retries. Degradando para contexto vazio.")
            return ""
