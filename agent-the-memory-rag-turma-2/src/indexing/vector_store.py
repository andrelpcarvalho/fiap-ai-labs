"""
Vector store para indexação RAG. Upsert de vetores + metadados.
Backend escolhido via config/memory_policy.yaml (vector_search.backend: chroma | vertex | mock).
"""

import json
import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_POLICY_PATH = Path("config/memory_policy.yaml")


def _load_vector_search_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_POLICY_PATH
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return (data.get("vector_search") or {}).copy()


def _get_chroma_collection(persist_directory: str, collection_name: str):
    import numpy as np
    if not hasattr(np, "float_"):
        np.float_ = np.float64
    if not hasattr(np, "int_"):
        np.int_ = np.int64
    import chromadb

    client = chromadb.PersistentClient(path=persist_directory)
    return client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})


def upsert_documents(
    ids: list[str],
    vectors: list[list[float]],
    metadatas: list[dict],
    *,
    config_path: Path | None = None,
    index_endpoint_id: str | None = None,
    project_id: str | None = None,
    location: str | None = None,
    use_mock_if_unconfigured: bool = True,
    mock_output_path: str | Path | None = None,
) -> None:
    """
    Insere ou atualiza documentos (id, vetor, metadados) no vector store.
    O backend é definido em config/memory_policy.yaml (vector_search.backend): chroma | vertex | mock.
    """
    vs_cfg = _load_vector_search_config(config_path)
    backend = (vs_cfg.get("backend") or "mock").lower()

    if backend == "chroma":
        chroma_cfg = vs_cfg.get("chroma") or {}
        persist_dir = chroma_cfg.get("persist_directory", "data/chroma")
        collection_name = chroma_cfg.get("collection_name", "customer_insights")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        collection = _get_chroma_collection(persist_dir, collection_name)
        documents = [m.get("content", "") for m in metadatas]
        meta_serializable = []
        for m in metadatas:
            row = {}
            for k, v in m.items():
                if k is None or not isinstance(k, str):
                    continue
                if v is None or isinstance(v, (str, int, float, bool)):
                    row[k] = v
                else:
                    row[k] = str(v)
            meta_serializable.append(row)
        collection.add(ids=ids, embeddings=vectors, documents=documents, metadatas=meta_serializable)
        logger.info("Vector store ChromaDB: %d documentos gravados em %s", len(ids), persist_dir)
        return

    if backend == "vertex":
        index_endpoint_id = index_endpoint_id or os.environ.get("VECTOR_SEARCH_ENDPOINT_ID")
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = location or os.environ.get("GOOGLE_CLOUD_LOCATION")
        vertex_cfg = vs_cfg.get("vertex") or {}
        index_id = vertex_cfg.get("index_id") or os.environ.get("VECTOR_SEARCH_INDEX_ID")
        gcs_bucket = vertex_cfg.get("gcs_bucket") or os.environ.get("VECTOR_SEARCH_GCS_BUCKET")
        if index_endpoint_id and project_id and location and index_id and gcs_bucket:
            try:
                _upsert_vertex(
                    ids,
                    vectors,
                    metadatas,
                    project_id=project_id,
                    location=location,
                    index_endpoint_id=index_endpoint_id,
                    index_id=index_id,
                    gcs_bucket=gcs_bucket,
                    vertex_cfg=vertex_cfg,
                )
                return
            except Exception as e:
                logger.warning("Falha ao escrever no Vertex Vector Search: %s. Usando mock.", e)
        if use_mock_if_unconfigured:
            _do_upsert_mock(ids, vectors, metadatas, vs_cfg, mock_output_path)
            return
        raise ValueError(
            "Vertex configurado como backend mas env (VECTOR_SEARCH_ENDPOINT_ID, INDEX_ID, GCS_BUCKET, etc.) ausente ou falhou."
        )

    if backend == "mock" or not backend:
        _do_upsert_mock(ids, vectors, metadatas, vs_cfg, mock_output_path)
        return

    raise ValueError(f"vector_search.backend inválido: {backend}. Use chroma, vertex ou mock.")


def _do_upsert_mock(
    ids: list[str],
    vectors: list[list[float]],
    metadatas: list[dict],
    vs_cfg: dict,
    mock_output_path: str | Path | None,
) -> None:
    mock_cfg = vs_cfg.get("mock") or {}
    path = mock_output_path or mock_cfg.get("path") or Path("data") / "vector_store_mock.jsonl"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _upsert_mock_file(ids, vectors, metadatas, path)
    logger.info("Vector store mock: %d documentos gravados em %s", len(ids), path)


def _upsert_mock_file(ids: list[str], vectors: list[list[float]], metadatas: list[dict], path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for i, vec, meta in zip(ids, vectors, metadatas):
            line = json.dumps({"id": i, "vector": vec, "metadata": meta}, ensure_ascii=False) + "\n"
            f.write(line)


def _upsert_vertex(
    ids: list[str],
    vectors: list[list[float]],
    metadatas: list[dict],
    *,
    project_id: str,
    location: str,
    index_endpoint_id: str,
    index_id: str,
    gcs_bucket: str,
    vertex_cfg: dict | None = None,
) -> None:
    """Faz upsert batch no Vertex AI Vector Search: JSONL no GCS + update index + content store local."""
    try:
        from google.cloud import aiplatform
        from google.cloud.aiplatform_v1 import IndexServiceClient
        from google.cloud.aiplatform_v1.types import Index as IndexProtoType, UpdateIndexRequest
        from google.cloud.storage import Client as GcsClient
        from google.protobuf import field_mask_pb2
        from google.protobuf import struct_pb2
    except ImportError as e:
        raise NotImplementedError(
            "google.cloud.aiplatform e google.cloud.storage necessários para Vertex vector store."
        ) from e

    vertex_cfg = vertex_cfg or {}
    content_store_path = vertex_cfg.get("content_store_path") or str(Path("data") / "vertex_content_store.jsonl")
    content_store_path = Path(content_store_path)
    content_store_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Gerar JSONL no formato Vertex: id + embedding
    import tempfile
    import time
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for i, (doc_id, vec) in enumerate(zip(ids, vectors)):
            content = (metadatas[i].get("content", "") if i < len(metadatas) else "") or ""
            line = json.dumps({"id": doc_id, "embedding": vec}, ensure_ascii=False) + "\n"
            f.write(line)
        tmp_path = f.name

    try:
        # 2) Upload para GCS
        prefix = vertex_cfg.get("gcs_prefix", "vertex_batch")
        blob_name = f"{prefix}/update_{int(time.time() * 1000)}.jsonl"
        gcs = GcsClient(project=project_id)
        bucket = gcs.bucket(gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(tmp_path, content_type="application/jsonl")
        gcs_uri = f"gs://{gcs_bucket}/{blob_name}"

        # 3) Atualizar índice (metadata contentsDeltaUri)
        is_complete = vertex_cfg.get("is_complete_overwrite", False)
        if not index_id.startswith("projects/"):
            index_name = f"projects/{project_id}/locations/{location}/indexes/{index_id}"
        else:
            index_name = index_id

        client = IndexServiceClient(
            client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        )
        metadata_struct = struct_pb2.Struct()
        metadata_struct.update({"contentsDeltaUri": gcs_uri, "isCompleteOverwrite": is_complete})
        index_update = IndexProtoType(name=index_name, metadata=metadata_struct)
        request = UpdateIndexRequest(
            index=index_update,
            update_mask=field_mask_pb2.FieldMask(paths=["metadata"]),
        )
        client.update_index(request=request)
        logger.info(
            "Vertex Vector Search: batch enviado para %s (%d documentos). Rebuild pode levar minutos.",
            gcs_uri,
            len(ids),
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 4) Content store local (id -> content) para consulta depois
    with open(content_store_path, "a", encoding="utf-8") as f:
        for i, doc_id in enumerate(ids):
            content = (metadatas[i].get("content", "") if i < len(metadatas) else "") or ""
            f.write(json.dumps({"id": doc_id, "content": content}, ensure_ascii=False) + "\n")
    logger.info("Vector store Vertex: content store atualizado em %s", content_store_path)
