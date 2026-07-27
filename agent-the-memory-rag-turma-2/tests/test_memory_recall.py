import asyncio
from pathlib import Path

from src.indexing.chunking import chunk_text
from src.indexing.embedding import embed_texts
from src.indexing.loaders import load_documents_from_file
from src.indexing.vector_store import upsert_documents
from src.memory_gateway import LongTermMemoryGateway


def test_ltm_gateway_graceful_degradation(tmp_path):
    """Valida se o gateway retorna mock quando backend=mock (async)."""
    policy = tmp_path / "memory_policy.yaml"
    policy.write_text(
        "vector_search:\n  backend: mock\n  max_documents: 3\n  min_similarity_score: 0.70\n",
        encoding="utf-8",
    )
    gw = LongTermMemoryGateway(config_path=policy)

    res = asyncio.run(gw.search_customer_insights("query: teste para sessao_premium"))
    assert "cliente é conservador" in res

    res = asyncio.run(gw.search_customer_insights("query_que_nao_da_match"))
    assert res == "Nenhum histórico prévio encontrado para este CPF."


def test_ltm_gateway_chroma_min_similarity_filter(tmp_path):
    """Chroma: documentos abaixo de min_similarity_score são filtrados; resultado ordenado por similaridade."""
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    policy = tmp_path / "memory_policy.yaml"
    policy.write_text(
        f"""vector_search:
  backend: chroma
  max_documents: 5
  min_similarity_score: 0.95
  chroma:
    persist_directory: {chroma_dir.as_posix()}
    collection_name: test_insights
""",
        encoding="utf-8",
    )
    # Indexar dois documentos com embedding mock (mesmo texto = mesmo vetor).
    texts = ["alpha", "beta"]
    vectors = embed_texts(texts, for_query=False)
    metadatas = [{"content": t, "source": "test"} for t in texts]
    upsert_documents(
        ids=["id1", "id2"],
        vectors=vectors,
        metadatas=metadatas,
        config_path=policy,
    )
    gw = LongTermMemoryGateway(config_path=policy)
    # Query "alpha": com mock, mesmo texto = distância 0 = similaridade 1.0; "beta" = distância > 0 = similaridade < 1.0.
    # Com min_similarity 0.95, apenas "alpha" deve passar.
    res = asyncio.run(gw.search_customer_insights("alpha"))
    assert "alpha" in res
    assert "beta" not in res


def test_rag_e2e_index_search_with_where(tmp_path):
    """
    E2E: indexar CSV com session_id, buscar com query + where_metadata por session_id,
    assert que o conteúdo do insight dessa sessão aparece no resultado.
    """
    csv_path = tmp_path / "insights.csv"
    csv_path.write_text(
        "session_id,tier,content\n"
        'sessao_premium,premium,"Cliente premium. Só aceita taxas abaixo de 1,0% a.m. Perfil conservador."\n'
        'sessao_002,standard,"Sessão anterior: recusou proposta de 1,2%."\n',
        encoding="utf-8",
    )
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    policy = tmp_path / "memory_policy.yaml"
    policy.write_text(
        f"""vector_search:
  backend: chroma
  max_documents: 5
  min_similarity_score: 0.0  # E2E: mock não reflete similaridade real; 0.0 garante que chunk filtrado por where apareça
  chroma:
    persist_directory: {chroma_dir.as_posix()}
    collection_name: e2e_insights
""",
        encoding="utf-8",
    )
    docs = load_documents_from_file(csv_path, csv_text_column="content")
    all_chunks = []
    chunk_id = 0
    for doc in docs:
        meta_base = dict(doc["metadata"])
        chunks = chunk_text(doc["text"], chunk_size=256, overlap=0, strategy="fixed")
        for i, c in enumerate(chunks):
            rec = {
                "content": c,
                "source": meta_base.get("source", csv_path.name),
                "chunk_index": i,
                "metadata": {k: v for k, v in meta_base.items() if k != "source"},
            }
            rec["metadata"]["chunk_id"] = str(chunk_id)
            all_chunks.append(rec)
            chunk_id += 1
    texts = [c["content"] for c in all_chunks]
    vectors = embed_texts(texts, for_query=False)
    ids = [c["metadata"]["chunk_id"] for c in all_chunks]
    metadatas = [
        {**c["metadata"], "content": c["content"], "source": c["source"]}
        for c in all_chunks
    ]
    upsert_documents(
        ids=ids,
        vectors=vectors,
        metadatas=metadatas,
        config_path=policy,
    )
    gw = LongTermMemoryGateway(config_path=policy)
    query = "Sessao: sessao_premium. Contexto: quero taxa menor"
    res = asyncio.run(
        gw.search_customer_insights(query=query, where_metadata={"session_id": "sessao_premium"})
    )
    assert "1,0%" in res or "conservador" in res or "premium" in res.lower()
