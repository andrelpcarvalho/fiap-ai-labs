"""
Lab 1 — Anatomia do Chunking.
Compara estratégias de chunking sobre os documentos de data/lab/.

Uso:
  python scripts/chunk_inspect.py
  python scripts/chunk_inspect.py --strategy fixed --size 128 --overlap 0
  python scripts/chunk_inspect.py --compare
  python scripts/chunk_inspect.py --file data/lab/lab_emprestimo.txt --show-chunks
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path

# Consoles Windows (cp1252/cp850) não representam "✂"/"✓"; força UTF-8 com fallback.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.indexing.chunking import chunk_text
from src.indexing.loaders import load_documents_from_file

DEFAULT_INPUTS = [
    repo_root / "data" / "lab" / "lab_conta_premium.pdf",
    repo_root / "data" / "lab" / "lab_tarifas.csv",
    repo_root / "data" / "lab" / "lab_emprestimo.txt",
]

STRATEGIES = ("fixed", "by_paragraph", "by_sentence", "recursive", "by_tokens", "by_source")


def _ends_mid_sentence(chunk: str) -> bool:
    """Heurística: chunk não termina em pontuação de fim de frase."""
    c = chunk.rstrip()
    if not c:
        return False
    return c[-1] not in ".!?;:"


def analyze_chunks(chunks: list[str]) -> dict:
    lengths = [len(c) for c in chunks]
    if not lengths:
        return {
            "n": 0,
            "avg": 0,
            "min": 0,
            "max": 0,
            "std": 0,
            "mid_sentence_pct": 0.0,
        }
    mid = sum(1 for c in chunks if _ends_mid_sentence(c))
    return {
        "n": len(chunks),
        "avg": statistics.mean(lengths),
        "min": min(lengths),
        "max": max(lengths),
        "std": statistics.pstdev(lengths) if len(lengths) > 1 else 0.0,
        "mid_sentence_pct": 100.0 * mid / len(chunks),
    }


def load_corpus(paths: list[Path]) -> list[tuple[str, str]]:
    """Retorna lista (source, text)."""
    docs: list[tuple[str, str]] = []
    for p in paths:
        if not p.exists():
            print(f"AVISO: arquivo não encontrado: {p}", file=sys.stderr)
            continue
        for doc in load_documents_from_file(p):
            docs.append((doc["metadata"].get("source", p.name), doc["text"]))
    return docs


def run_one(
    docs: list[tuple[str, str]],
    strategy: str,
    size: int,
    overlap: int,
    show_chunks: bool,
) -> None:
    all_chunks: list[str] = []
    print(f"\n=== strategy={strategy}  size={size}  overlap={overlap} ===")
    for source, text in docs:
        chunks = chunk_text(text, chunk_size=size, overlap=overlap, strategy=strategy, source=source)
        stats = analyze_chunks(chunks)
        print(
            f"  [{source}] n={stats['n']:3d}  "
            f"avg={stats['avg']:6.1f}  min={stats['min']:4d}  max={stats['max']:4d}  "
            f"std={stats['std']:5.1f}  mid_sentence={stats['mid_sentence_pct']:5.1f}%"
        )
        if show_chunks:
            for i, c in enumerate(chunks):
                preview = re.sub(r"\s+", " ", c)[:120]
                flag = "✂" if _ends_mid_sentence(c) else "✓"
                print(f"    {flag} [{i}] ({len(c)} chars) {preview}...")
        all_chunks.extend(chunks)
    total = analyze_chunks(all_chunks)
    print(
        f"  TOTAL     n={total['n']:3d}  "
        f"avg={total['avg']:6.1f}  min={total['min']:4d}  max={total['max']:4d}  "
        f"mid_sentence={total['mid_sentence_pct']:5.1f}%"
    )


def run_compare(docs: list[tuple[str, str]], sizes: list[int], overlap: int) -> None:
    print("\n" + "=" * 78)
    print(f"{'strategy':<14} {'size':>5} {'n':>4} {'avg':>7} {'min':>5} {'max':>5} {'mid%':>7}")
    print("-" * 78)
    for strategy in STRATEGIES:
        for size in sizes:
            ov = overlap if strategy in ("fixed", "by_tokens") else 0
            all_chunks: list[str] = []
            for source, text in docs:
                all_chunks.extend(
                    chunk_text(text, chunk_size=size, overlap=overlap, strategy=strategy, source=source)
                )
            s = analyze_chunks(all_chunks)
            print(
                f"{strategy:<14} {size:>5} {s['n']:>4} {s['avg']:>7.1f} "
                f"{s['min']:>5} {s['max']:>5} {s['mid_sentence_pct']:>6.1f}%"
            )
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspeciona chunking (Lab 1)")
    parser.add_argument("--strategy", choices=STRATEGIES, default="recursive")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[128, 512, 2048],
        help="Tamanhos para --compare",
    )
    parser.add_argument("--compare", action="store_true", help="Tabela comparativa")
    parser.add_argument("--show-chunks", action="store_true", help="Mostra preview dos chunks")
    parser.add_argument("--file", type=Path, action="append", help="Arquivo(s) de entrada")
    args = parser.parse_args()

    paths = args.file if args.file else DEFAULT_INPUTS
    # Gera PDF se necessário
    pdf = repo_root / "data" / "lab" / "lab_conta_premium.pdf"
    if any(p.resolve() == pdf.resolve() or p.name == pdf.name for p in paths) and not pdf.exists():
        import runpy

        runpy.run_path(str(repo_root / "scripts" / "generate_lab_pdf.py"), run_name="__main__")

    docs = load_corpus(paths)
    if not docs:
        print("Nenhum documento carregado.", file=sys.stderr)
        return 1

    total_chars = sum(len(t) for _, t in docs)
    print(f"Corpus: {len(docs)} documento(s), {total_chars} caracteres")
    for src, t in docs:
        print(f"  - {src}: {len(t)} chars")

    if args.compare:
        run_compare(docs, args.sizes, args.overlap)
    else:
        run_one(docs, args.strategy, args.size, args.overlap, args.show_chunks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
