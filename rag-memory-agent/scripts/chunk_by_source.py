# scripts/chunk_by_source.py
from pathlib import Path
import csv
import sys
from src.indexing import _chunk_recursive, extract_pdf_text # reaproveita o que já existe

def chunk_by_source(path: str, chunk_size: int = 128, overlap: int = 16):
    p = Path(path)
    if p.suffix.lower() == ".csv":
    # unidade semântica já é a linha -> nenhum chunking adicional
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            return [
                {"text": ",".join(row), "source": p.name, "row": i}
                for i, row in enumerate(reader)
                if any(cell.strip() for cell in row)
            ]
    # .txt / .pdf -> reaproveita o recursive já testado no pipeline
    text = p.read_text(encoding="utf-8") if p.suffix == ".txt" else extract_pdf_text(p)
    return _chunk_recursive(text, size=chunk_size, overlap=overlap, source=p.name)

if __name__ == "__main__":
    import sys
    chunks = chunk_by_source(sys.argv[1])
    print(f"{len(chunks)} chunks gerados")
    for c in chunks[:5]:
        print("-", c["text"][:80])