"""
CLI do pipeline de indexação RAG: CSV, JSON, PDF, TXT -> chunking -> [embedding -> vector store].
Uso: python -m src.indexing --config config/indexing.yaml --input f1.csv f2.json [--output chunks.json] [--push]
Carrega .env da raiz do projeto (GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION) para usar Vertex nos embeddings.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Carregar .env da raiz do projeto antes dos imports que usam env (embedding)
_repo_root = Path(__file__).resolve().parent.parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_repo_root / ".env", override=True)
except ImportError:
    pass

# Reduz ruído de telemetria do Chroma em labs
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
import yaml

from src.indexing.chunking import chunk_text
from src.indexing.loaders import load_documents_from_file
from src.indexing.embedding import embed_texts
from src.indexing.vector_store import upsert_documents

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run(
    config_path: Path,
    input_paths: list[Path],
    output_path: Path | None,
    push: bool,
) -> None:
    config = load_config(config_path)
    chunk_cfg = config.get("chunking") or {}
    chunk_size = int(chunk_cfg.get("chunk_size_chars", 512))
    overlap = int(chunk_cfg.get("overlap_chars", 64))
    strategy = chunk_cfg.get("strategy", "fixed")

    csv_col = (config.get("csv") or {}).get("text_column", "content")
    json_path = (config.get("json") or {}).get("text_path", "content")
    pdf_merge = (config.get("pdf") or {}).get("merge_pages", True)
    emb_cfg = config.get("embedding") or {}
    vs_cfg = config.get("vector_store") or {}

    all_chunks = []
    chunk_id = 0
    for inp in input_paths:
        if not inp.exists():
            logger.warning("Arquivo não encontrado: %s", inp)
            continue
        docs = load_documents_from_file(
            inp,
            csv_text_column=csv_col,
            json_text_path=json_path,
            pdf_merge_pages=pdf_merge,
        )
        for doc in docs:
            text = doc["text"]
            meta_base = dict(doc["metadata"])
            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap, strategy=strategy)
            for i, c in enumerate(chunks):
                rec = {
                    "content": c,
                    "source": meta_base.get("source", inp.name),
                    "chunk_index": i,
                    "metadata": {k: v for k, v in meta_base.items() if k != "source"},
                }
                rec["metadata"]["chunk_id"] = str(chunk_id)
                all_chunks.append(rec)
                chunk_id += 1

    if not all_chunks:
        logger.warning("Nenhum chunk gerado.")
        return

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        logger.info("Chunks gravados: %s (%d)", output_path, len(all_chunks))

    if push:
        texts = [c["content"] for c in all_chunks]
        vectors = embed_texts(
            texts,
            model=emb_cfg.get("model"),
            batch_size=int(emb_cfg.get("batch_size", 5)),
            backend=emb_cfg.get("backend"),
            config_path=config_path,
        )
        ids = [c["metadata"].get("chunk_id", str(i)) for i, c in enumerate(all_chunks)]
        metadatas = [{**c["metadata"], "content": c["content"], "source": c["source"]} for c in all_chunks]
        upsert_documents(
            ids,
            vectors,
            metadatas,
            config_path=Path("config/memory_policy.yaml"),
            use_mock_if_unconfigured=vs_cfg.get("use_mock_if_unconfigured", True),
            mock_output_path=os.environ.get("INDEXING_MOCK_OUTPUT"),
        )
        logger.info("Push concluído: %d documentos.", len(ids))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de indexação RAG (CSV, JSON, PDF, TXT)")
    parser.add_argument("--config", type=Path, default=Path("config/indexing.yaml"), help="Arquivo YAML de configuração")
    parser.add_argument("--input", "-i", type=Path, nargs="+", required=True, help="Arquivos ou diretórios de entrada")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Arquivo JSON de saída (chunks)")
    parser.add_argument("--push", action="store_true", help="Gerar embeddings e enviar ao vector store")
    args = parser.parse_args()

    inputs = []
    for p in args.input:
        p = Path(p)
        if p.is_dir():
            for ext in ("*.csv", "*.json", "*.pdf", "*.txt"):
                inputs.extend(p.glob(ext))
        else:
            inputs.append(p)

    if not inputs:
        logger.error("Nenhum arquivo de entrada (CSV, JSON, PDF ou TXT).")
        sys.exit(1)

    run(args.config, inputs, args.output, args.push)


if __name__ == "__main__":
    main()
