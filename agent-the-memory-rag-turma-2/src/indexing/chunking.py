"""
Chunking configurável para pipeline de indexação RAG.
Estratégias: fixed, by_paragraph, by_sentence, recursive.
"""

import re


# Separadores para recursive (do maior ao menor): parágrafo, linha, sentença, palavra
_RECURSIVE_SEPARATORS = [
    "\n\n",
    "\n",
    re.compile(r"(?<=[.!?])\s+"),
    " ",
]


def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[str]:
    """
    Divide texto em pedaços.

    Args:
        text: texto a segmentar.
        chunk_size: tamanho máximo do chunk (caracteres, ou tokens se strategy=by_tokens).
        overlap: sobreposição entre chunks (chars em fixed; tokens em by_tokens).
        strategy: "fixed" | "by_paragraph" | "by_sentence" | "recursive" | "by_tokens".

    Returns:
        Lista de strings (chunks).
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if strategy == "by_paragraph":
        return _chunk_by_paragraph(text, chunk_size)
    if strategy == "by_sentence":
        return _chunk_by_sentence(text, chunk_size)
    if strategy == "by_tokens":
        return _chunk_by_tokens(text, chunk_size, overlap)
    if strategy == "recursive":
        return _chunk_recursive(text, chunk_size)
    return _chunk_fixed(text, chunk_size, overlap)


def _chunk_by_tokens(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """
    Chunk por tokens (tiktoken encoding cl100k_base).
    chunk_size e overlap são contados em tokens, não em caracteres.
    """
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
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


def _chunk_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    overlap = min(max(0, overlap), chunk_size - 1)
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if overlap else end
    return chunks


def _chunk_by_sentence(text: str, chunk_size: int) -> list[str]:
    # Quebra em sentenças: após . ! ? seguido de espaço ou fim
    raw = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in raw if s.strip()]
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s_len = len(s) + 1  # +1 pelo espaço entre sentenças
        if current_len + s_len > chunk_size and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(s)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def _chunk_by_paragraph(text: str, chunk_size: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        p_len = len(p) + 2  # +2 por \n\n
        if current_len + p_len > chunk_size and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(p)
        current_len += p_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_by_sep(text: str, sep) -> list[str]:
    """Separa text por sep (str ou re.Pattern)."""
    if isinstance(sep, re.Pattern):
        return [s.strip() for s in sep.split(text) if s.strip()]
    return [s.strip() for s in text.split(sep) if s.strip()]


def _chunk_recursive(text: str, chunk_size: int, separators: list | None = None) -> list[str]:
    """
    Recursive: tenta quebrar por parágrafo -> linha -> sentença -> palavra;
    pedaços maiores que chunk_size são quebrados no próximo nível.
    """
    if separators is None:
        separators = _RECURSIVE_SEPARATORS
    if len(text) <= chunk_size:
        return [text] if text else []
    if not separators:
        return _chunk_fixed(text, chunk_size, 0)
    sep = separators[0]
    rest_seps = separators[1:]
    parts = _split_by_sep(text, sep)
    join_char = "\n\n" if sep == "\n\n" else "\n" if sep == "\n" else " "
    chunks = []
    current = []
    current_len = 0
    for part in parts:
        if len(part) <= chunk_size:
            part_len = len(part) + (len(join_char) if current else 0)
            if current_len + part_len > chunk_size and current:
                chunks.append(join_char.join(current))
                current = []
                current_len = 0
            current.append(part)
            current_len += part_len
        else:
            if current:
                chunks.append(join_char.join(current))
                current = []
                current_len = 0
            chunks.extend(_chunk_recursive(part, chunk_size, rest_seps))
    if current:
        chunks.append(join_char.join(current))
    return chunks
