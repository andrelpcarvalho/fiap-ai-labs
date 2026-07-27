"""
Solução de referência — Lab 3: chunking by_tokens.

NÃO importe este módulo no código de produção.
Use para comparar com sua implementação em src/indexing/chunking.py.
"""

from __future__ import annotations


def chunk_by_tokens(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """
    Divide texto em janelas de `chunk_size` tokens (tiktoken cl100k_base),
    com sobreposição de `overlap` tokens.
    """
    import tiktoken

    if not text or not text.strip():
        return []

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text.strip())
    if not tokens:
        return []

    overlap = min(max(0, overlap), max(0, chunk_size - 1))
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        piece = enc.decode(tokens[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= len(tokens):
            break
        start = end - overlap if overlap else end
    return chunks
