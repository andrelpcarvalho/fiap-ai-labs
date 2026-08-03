"""
Embedding para indexação RAG.
Backends: local (sentence-transformers), vertex (Google Gen AI SDK) ou mock.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_INDEXING_CONFIG = Path("config/indexing.yaml")
DEFAULT_LOCAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
LOCAL_EMBEDDING_DIM = 384
MOCK_EMBEDDING_DIM = 768

_local_model_cache: dict[str, object] = {}


def load_embedding_config(config_path: Path | None = None) -> dict:
    """Carrega seção embedding de config/indexing.yaml."""
    path = config_path or DEFAULT_INDEXING_CONFIG
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return (data.get("embedding") or {}).copy()


def resolve_backend(explicit: str | None = None, config_path: Path | None = None) -> str:
    """
    Resolve backend: argumento > config > env EMBEDDING_BACKEND > auto.
    Auto: vertex se GCP configurado; senão local se sentence-transformers disponível; senão mock.
    """
    if explicit:
        return explicit.lower()
    cfg = load_embedding_config(config_path)
    if cfg.get("backend"):
        return str(cfg["backend"]).lower()
    env_backend = os.environ.get("EMBEDDING_BACKEND")
    if env_backend:
        return env_backend.lower()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GOOGLE_CLOUD_REGION")
    if project_id and location:
        return "vertex"
    try:
        import sentence_transformers  # noqa: F401

        return "local"
    except ImportError:
        return "mock"


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
    project_id: str | None = None,
    location: str | None = None,
    batch_size: int = 5,
    for_query: bool = False,
    backend: str | None = None,
    config_path: Path | None = None,
) -> list[list[float]]:
    """
    Gera embeddings para uma lista de textos.

    Args:
        texts: lista de strings a embedar.
        model: modelo (local ou Vertex); default vem da config.
        project_id: projeto GCP (default: GOOGLE_CLOUD_PROJECT).
        location: região (default: GOOGLE_CLOUD_LOCATION).
        batch_size: tamanho do lote para a API Vertex.
        for_query: se True, usa RETRIEVAL_QUERY (Vertex) / encode query (local).
        backend: local | vertex | mock (default: resolve_backend).
        config_path: caminho do indexing.yaml.

    Returns:
        Lista de vetores (listas de float), um por texto.
    """
    if not texts:
        return []

    cfg = load_embedding_config(config_path)
    chosen = resolve_backend(backend, config_path)
    model = model or cfg.get("model") or (
        DEFAULT_LOCAL_MODEL if chosen == "local" else "text-multilingual-embedding-002"
    )
    batch_size = int(cfg.get("batch_size", batch_size))

    if chosen == "local":
        try:
            return _embed_local(texts, model=model, for_query=for_query)
        except ImportError:
            logger.warning(
                "sentence-transformers não instalado. "
                'Rode: pip install -e ".[lab]". Usando embeddings mock.'
            )
            return [_mock_embed(t) for t in texts]

    if chosen == "vertex":
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get(
            "GOOGLE_CLOUD_REGION"
        )
        if project_id and location:
            return _embed_vertex(
                texts,
                model=model,
                project_id=project_id,
                location=location,
                batch_size=batch_size,
                for_query=for_query,
            )
        logger.warning(
            "Backend vertex solicitado mas GOOGLE_CLOUD_PROJECT/LOCATION ausentes. Usando mock."
        )
        return [_mock_embed(t) for t in texts]

    if chosen == "mock":
        logger.warning(
            "Usando embeddings mock (hash) — semântica limitada. "
            'Para embeddings reais locais: pip install -e ".[lab]" e backend: local.'
        )
        return [_mock_embed(t) for t in texts]

    raise ValueError(f"embedding.backend inválido: {chosen}. Use local, vertex ou mock.")


def _embed_local(texts: list[str], *, model: str, for_query: bool = False) -> list[list[float]]:
    """Embeddings locais via sentence-transformers (offline após download do modelo)."""
    from sentence_transformers import SentenceTransformer

    if model not in _local_model_cache:
        logger.info("Carregando modelo local de embedding: %s (primeiro uso pode baixar ~470MB)", model)
        _local_model_cache[model] = SentenceTransformer(model)
    encoder: SentenceTransformer = _local_model_cache[model]  # type: ignore[assignment]
    # sentence-transformers trata query/doc de forma similar para MiniLM; normalize para cosine
    vectors = encoder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [v.tolist() for v in vectors]


def _mock_embed(text: str, dim: int = MOCK_EMBEDDING_DIM) -> list[float]:
    """Vetor determinístico por hash do texto (reprodutível para testes)."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    base = [(int(h[i : i + 2], 16) / 255.0 - 0.5) for i in range(0, min(64, len(h) - 1), 2)]
    while len(base) < dim:
        base = (base * ((dim // len(base)) + 1))[:dim]
    return base


def _embed_vertex(
    texts: list[str],
    *,
    model: str,
    project_id: str,
    location: str,
    batch_size: int,
    for_query: bool = False,
) -> list[list[float]]:
    """Usa Google Gen AI SDK (google-genai) com Vertex AI para embeddings."""
    from google import genai
    from google.genai.types import EmbedContentConfig

    task_type = "RETRIEVAL_QUERY" if for_query else "RETRIEVAL_DOCUMENT"
    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = [t[:20_000] for t in texts[i : i + batch_size]]
        result = client.models.embed_content(
            model=model,
            contents=batch,
            config=EmbedContentConfig(task_type=task_type),
        )
        if not result.embeddings:
            continue
        for emb in result.embeddings:
            vec = getattr(emb, "values", None) or emb
            if vec is not None:
                all_embeddings.append(list(vec))
    return all_embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade cosseno entre dois vetores (utilitário para labs/testes)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
