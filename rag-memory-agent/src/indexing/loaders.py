"""
Loaders para pipeline de indexação: CSV, JSON, PDF e TXT.
Retornam lista de documentos: cada um com 'text' e 'metadata' (source, etc.).
"""

import csv
import json
from pathlib import Path


def load_documents_from_file(
    path: str | Path,
    *,
    csv_text_column: str = "content",
    json_text_path: str = "content",
    pdf_merge_pages: bool = True,
) -> list[dict]:
    """
    Carrega documentos de um arquivo (CSV, JSON, PDF ou TXT).

    Returns:
        Lista de dicts: [{"text": str, "metadata": dict}, ...]
        metadata inclui "source" (nome do arquivo) e, quando aplicável,
        session_id, tier, page, tipo, etc.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path, text_column=csv_text_column)
    if suffix == ".json":
        return _load_json(path, text_path=json_text_path)
    if suffix == ".pdf":
        return _load_pdf(path, merge_pages=pdf_merge_pages)
    if suffix == ".txt":
        return _load_txt(path)
    raise ValueError(f"Formato não suportado: {suffix}. Use .csv, .json, .pdf ou .txt.")


def _load_csv(path: Path, text_column: str = "content") -> list[dict]:
    docs = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get(text_column) or row.get("text", "")
            if not (text and str(text).strip()):
                continue
            metadata = {"source": path.name}
            for k, v in row.items():
                if k != text_column and k != "text" and v:
                    metadata[k] = v
            docs.append({"text": str(text).strip(), "metadata": metadata})
    return docs


def _get_nested(data: dict, path: str):  # noqa: ANN201
    keys = path.split(".")
    cur = data
    for k in keys:
        cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _load_json(path: Path, text_path: str = "content") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    if isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            text = _get_nested(item, text_path) or item.get("body") or item.get("text")
            if not text:
                continue
            metadata = {"source": path.name, "index": i}
            for k, v in item.items():
                if k not in ("content", "body", "text", "data"):
                    metadata[k] = v
            docs.append({"text": str(text).strip(), "metadata": metadata})
    elif isinstance(data, dict):
        text = _get_nested(data, text_path) or data.get("content") or data.get("body") or data.get("text")
        if text:
            metadata = {"source": path.name}
            for k, v in data.items():
                if k not in ("content", "body", "text", "data"):
                    metadata[k] = v
            docs.append({"text": str(text).strip(), "metadata": metadata})
    return docs


def _load_txt(path: Path, encoding: str = "utf-8") -> list[dict]:
    """Carrega um arquivo TXT como um único documento."""
    with open(path, encoding=encoding) as f:
        text = f.read()
    if not text.strip():
        return []
    return [{"text": text.strip(), "metadata": {"source": path.name}}]


def _load_pdf(path: Path, merge_pages: bool = True) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError("Leitura de PDF requer: pip install pypdf") from e

    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        if t.strip():
            pages.append((i + 1, t.strip()))
    if not pages:
        return []

    if merge_pages:
        full = "\n\n".join(t for _, t in pages)
        return [{"text": full, "metadata": {"source": path.name, "pages": len(pages)}}]
    return [
        {"text": t, "metadata": {"source": path.name, "page": num}}
        for num, t in pages
    ]
