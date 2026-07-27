"""Testes do pipeline de indexação RAG (chunking, loaders e embedding)."""

import pytest
from pathlib import Path

from src.indexing.chunking import chunk_text
from src.indexing.loaders import load_documents_from_file
from src.indexing.embedding import embed_texts


def test_chunk_text_fixed():
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=300, overlap=50, strategy="fixed")
    assert len(chunks) >= 3
    assert all(len(c) <= 300 for c in chunks)


def test_chunk_text_by_paragraph():
    text = "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três."
    chunks = chunk_text(text, chunk_size=100, strategy="by_paragraph")
    assert len(chunks) >= 1
    assert "Parágrafo" in chunks[0]


def test_chunk_text_empty():
    assert chunk_text("", chunk_size=100) == []
    assert chunk_text("   ", chunk_size=100) == []


def test_load_csv(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(
        "session_id,tier,content\n"
        "s1,premium,Texto do cliente premium.",
        encoding="utf-8",
    )
    docs = load_documents_from_file(csv_path, csv_text_column="content")
    assert len(docs) == 1
    assert docs[0]["text"] == "Texto do cliente premium."
    assert docs[0]["metadata"]["session_id"] == "s1"
    assert docs[0]["metadata"]["tier"] == "premium"


def test_load_json(tmp_path):
    json_path = tmp_path / "test.json"
    json_path.write_text(
        '[{"content": "Regra um.", "tipo": "faq"}]',
        encoding="utf-8",
    )
    docs = load_documents_from_file(json_path, json_text_path="content")
    assert len(docs) == 1
    assert docs[0]["text"] == "Regra um."
    assert docs[0]["metadata"]["tipo"] == "faq"


def test_load_txt(tmp_path):
    txt_path = tmp_path / "doc.txt"
    txt_path.write_text("Conteúdo do arquivo TXT.\nSegunda linha.", encoding="utf-8")
    docs = load_documents_from_file(txt_path)
    assert len(docs) == 1
    assert docs[0]["text"] == "Conteúdo do arquivo TXT.\nSegunda linha."
    assert docs[0]["metadata"]["source"] == "doc.txt"


def test_embed_texts_mock_default_document():
    """Embedding mock com for_query=False (indexação) retorna vetores de mesma dimensão."""
    texts = ["um texto", "outro texto"]
    out = embed_texts(texts, for_query=False, backend="mock")
    assert len(out) == 2
    assert all(len(v) == len(out[0]) for v in out)
    assert len(out[0]) > 0
    assert out[0] != out[1]


def test_embed_texts_mock_for_query():
    """Embedding mock com for_query=True (consulta) retorna vetores; API aceita parâmetro."""
    texts = ["query de busca"]
    out = embed_texts(texts, for_query=True, backend="mock")
    assert len(out) == 1
    assert len(out[0]) > 0


def test_embed_texts_local_semantic_similarity():
    """Embedding local: 'tarifa de TED' mais próximo de texto de tarifas do que de empréstimo."""
    pytest.importorskip("sentence_transformers")
    from src.indexing.embedding import cosine_similarity

    query = "Qual a tarifa de TED da conta premium?"
    doc_tarifas = (
        "TED: isento para conta premium até 5 por mês. Após isso, R$ 15,00 por TED."
    )
    doc_emprestimo = (
        "Cliente premium: taxa a partir de 0,85% a.m., prazo de até 60 meses."
    )
    vectors = embed_texts(
        [query, doc_tarifas, doc_emprestimo],
        backend="local",
        for_query=False,
    )
    assert len(vectors) == 3
    assert all(len(v) == len(vectors[0]) for v in vectors)
    sim_tarifas = cosine_similarity(vectors[0], vectors[1])
    sim_emprestimo = cosine_similarity(vectors[0], vectors[2])
    assert sim_tarifas > sim_emprestimo
