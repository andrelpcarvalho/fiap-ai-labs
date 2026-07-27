"""
Lab 3 — testes do chunker by_tokens.
Esqueleto + asserts: devem passar com a implementação em src/indexing/chunking.py.
"""

import tiktoken

from src.indexing.chunking import chunk_text


def test_by_tokens_empty():
    assert chunk_text("", chunk_size=32, strategy="by_tokens") == []
    assert chunk_text("   ", chunk_size=32, strategy="by_tokens") == []


def test_by_tokens_respects_token_limit():
    enc = tiktoken.get_encoding("cl100k_base")
    # Texto longo o suficiente para vários chunks
    text = "Cliente premium taxa 0,85 por cento ao mes. " * 40
    chunk_size = 32
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=0, strategy="by_tokens")
    assert len(chunks) >= 2
    # Decode→encode pode variar ±1 token na borda; aceitamos folga pequena.
    for c in chunks:
        assert len(enc.encode(c)) <= chunk_size + 2


def test_by_tokens_overlap_increases_count():
    text = "Recusa de taxa dispara handoff apos tres tentativas. " * 30
    no_overlap = chunk_text(text, chunk_size=24, overlap=0, strategy="by_tokens")
    with_overlap = chunk_text(text, chunk_size=24, overlap=8, strategy="by_tokens")
    assert len(with_overlap) >= len(no_overlap)


def test_by_tokens_roundtrip_covers_content():
    text = "TED gratuito ate cinco por mes na conta premium."
    chunks = chunk_text(text, chunk_size=64, overlap=0, strategy="by_tokens")
    assert len(chunks) == 1
    assert "TED" in chunks[0]
    assert "premium" in chunks[0]


def test_chunk_text_dispatches_by_tokens():
    text = "a b c d e f g h i j " * 20
    chunks = chunk_text(text, chunk_size=16, overlap=2, strategy="by_tokens")
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert len(chunks) >= 1
