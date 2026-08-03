"""
Lab 2 — Avalia qualidade de retrieval sob diferentes configs de chunking.

Indexa o corpus de data/lab/ em coleções Chroma separadas e mede hit rate@k
contra data/lab/golden_set.json, usando embeddings locais (ou mock).

Uso:
  python scripts/eval_retrieval.py
  python scripts/eval_retrieval.py --k 3 --persist-dir data/chroma_lab2
  python scripts/eval_retrieval.py --configs fixed_128_o0 recursive_512
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Evita warnings de telemetria do Chroma durante o lab
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Consoles Windows (cp1252/cp850) podem quebrar ao imprimir previews; força UTF-8 com fallback.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.indexing.chunking import chunk_text
from src.indexing.embedding import embed_texts
from src.indexing.loaders import load_documents_from_file
from src.indexing.vector_store import _get_chroma_collection

DEFAULT_INPUTS = [
    repo_root / "data" / "lab" / "lab_conta_premium.pdf",
    repo_root / "data" / "lab" / "lab_tarifas.csv",
    repo_root / "data" / "lab" / "lab_emprestimo.txt",
]
GOLDEN_PATH = repo_root / "data" / "lab" / "golden_set.json"


@dataclass
class ChunkConfig:
    name: str
    strategy: str
    size: int
    overlap: int


DEFAULT_CONFIGS = [
    ChunkConfig("fixed_128_o0", "fixed", 128, 0),
    ChunkConfig("fixed_512_o64", "fixed", 512, 64),
    ChunkConfig("recursive_512", "recursive", 512, 0),
    ChunkConfig("by_tokens_128", "by_tokens", 128, 16),
]


def ensure_pdf() -> None:
    pdf = repo_root / "data" / "lab" / "lab_conta_premium.pdf"
    if not pdf.exists():
        import runpy

        runpy.run_path(str(repo_root / "scripts" / "generate_lab_pdf.py"), run_name="__main__")


def load_docs(paths: list[Path]) -> list[dict]:
    docs = []
    for p in paths:
        if not p.exists():
            print(f"AVISO: pulando {p}", file=sys.stderr)
            continue
        docs.extend(load_documents_from_file(p))
    return docs


def build_chunks(docs: list[dict], cfg: ChunkConfig) -> list[dict]:
    chunks = []
    chunk_id = 0
    for doc in docs:
        text = doc["text"]
        source = doc["metadata"].get("source", "")
        parts = chunk_text(
            text,
            chunk_size=cfg.size,
            overlap=cfg.overlap,
            strategy=cfg.strategy,
        )
        for i, c in enumerate(parts):
            chunks.append(
                {
                    "id": f"{cfg.name}_{chunk_id}",
                    "content": c,
                    "source": source,
                    "chunk_index": i,
                }
            )
            chunk_id += 1
    return chunks


def index_collection(persist_dir: Path, collection_name: str, chunks: list[dict], backend: str) -> int:
    if persist_dir.exists():
        # Só limpa a collection via recreate: apaga e recria client dir se for isolado
        pass
    persist_dir.mkdir(parents=True, exist_ok=True)
    # Remove collection anterior se existir
    import chromadb

    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    if not chunks:
        return 0

    texts = [c["content"] for c in chunks]
    vectors = embed_texts(texts, backend=backend, for_query=False)
    ids = [c["id"] for c in chunks]
    metadatas = [
        {"content": c["content"], "source": c["source"], "chunk_index": c["chunk_index"]}
        for c in chunks
    ]
    collection = _get_chroma_collection(str(persist_dir), collection_name)
    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    return len(chunks)


def hit(doc: str, item: dict) -> bool:
    needles = item.get("must_contain") or []
    if not needles:
        return False
    text = doc or ""
    if item.get("must_contain_any"):
        return any(n in text for n in needles)
    return all(n in text for n in needles)


def evaluate(
    persist_dir: Path,
    collection_name: str,
    golden: list[dict],
    k: int,
    backend: str,
    min_sim: float,
) -> dict:
    collection = _get_chroma_collection(str(persist_dir), collection_name)
    hits = 0
    details = []
    for item in golden:
        q = item["question"]
        q_emb = embed_texts([q], backend=backend, for_query=True)
        results = collection.query(
            query_embeddings=q_emb,
            n_results=k,
            include=["documents", "distances", "metadatas"],
        )
        docs = (results.get("documents") or [[]])[0] or []
        dists = (results.get("distances") or [[]])[0] or []
        # Filtra por similaridade aproximada
        kept = []
        for doc, dist in zip(docs, dists):
            sim = max(0.0, 1.0 - float(dist))
            if sim >= min_sim:
                kept.append(doc)
        ok = any(hit(d, item) for d in kept)
        if ok:
            hits += 1
        details.append(
            {
                "id": item["id"],
                "hit": ok,
                "n_returned": len(kept),
                "preview": (kept[0][:80] + "...") if kept else "",
            }
        )
    n = len(golden) or 1
    return {"hits": hits, "total": len(golden), "hit_rate": hits / n, "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval retrieval × chunking (Lab 2)")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--min-sim", type=float, default=0.20)
    parser.add_argument("--backend", default="local", choices=["local", "mock", "vertex"])
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=repo_root / "data" / "chroma_lab2",
        help="Diretório Chroma isolado para o lab (não mistura com data/chroma)",
    )
    parser.add_argument(
        "--configs",
        nargs="*",
        default=None,
        help="Nomes de configs a rodar (default: todas)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Apaga o persist-dir antes de indexar",
    )
    args = parser.parse_args()

    ensure_pdf()
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        golden = json.load(f)

    docs = load_docs(DEFAULT_INPUTS)
    if not docs:
        print("Nenhum documento carregado.", file=sys.stderr)
        return 1

    configs = DEFAULT_CONFIGS
    if args.configs:
        wanted = set(args.configs)
        configs = [c for c in DEFAULT_CONFIGS if c.name in wanted]
        if not configs:
            print(f"Nenhuma config válida em {args.configs}", file=sys.stderr)
            return 1

    if args.clean and args.persist_dir.exists():
        shutil.rmtree(args.persist_dir)

    print(f"Backend embedding: {args.backend}")
    print(f"Persist dir: {args.persist_dir}")
    print(f"Golden set: {len(golden)} perguntas | k={args.k} | min_sim={args.min_sim}")
    print()
    print(f"{'config':<18} {'chunks':>6} {'hits':>6} {'hit@'+str(args.k):>8}")
    print("-" * 46)

    summary = []
    for cfg in configs:
        chunks = build_chunks(docs, cfg)
        n = index_collection(args.persist_dir, cfg.name, chunks, args.backend)
        result = evaluate(
            args.persist_dir,
            cfg.name,
            golden,
            args.k,
            args.backend,
            args.min_sim,
        )
        print(
            f"{cfg.name:<18} {n:>6} {result['hits']:>3}/{result['total']:<2} "
            f"{result['hit_rate']*100:>7.1f}%"
        )
        if args.verbose:
            for d in result["details"]:
                mark = "OK" if d["hit"] else "MISS"
                print(f"    [{mark}] {d['id']}: {d['preview']}")
        summary.append({"config": cfg.name, **{k: result[k] for k in ("hits", "total", "hit_rate")}})

    out_path = repo_root / "out" / "lab2_eval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nResumo gravado em {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
