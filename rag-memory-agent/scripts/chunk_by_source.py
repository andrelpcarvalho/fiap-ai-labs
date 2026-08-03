# scripts/chunk_by_source.py
from pathlib import Path
import csv
from src.indexing.chunking import _chunk_recursive
from src.indexing.loaders import load_documents_from_file

def chunk_by_source(path: str, chunk_size: int = 128, overlap: int = 16):
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # pula o cabeçalho
            return [
                {"text": ",".join(row), "source": p.name, "row": i}
                for i, row in enumerate(reader)
                if any(cell.strip() for cell in row)
            ]
    # .txt / .pdf -> usa o loader real e delega pro recursive
    docs = load_documents_from_file(p)
    text = "\n\n".join(doc["text"] for doc in docs)
    return [
        {"text": chunk, "source": p.name, "row": i}
        for i, chunk in enumerate(_chunk_recursive(text, chunk_size))
    ]

if __name__ == "__main__":
    import sys
    chunks = chunk_by_source(sys.argv[1])
    print(f"{len(chunks)} chunks gerados")
    for c in chunks[:5]:
        print("-", c["text"][:80])