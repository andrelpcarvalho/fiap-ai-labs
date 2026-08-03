# tests/test_chunking_by_source.py
from src.indexing.chunking import chunk_text

def test_by_source_csv_one_chunk_per_line():
    csv_text = "linha1\nlinha2\nlinha3\n"
    chunks = chunk_text(csv_text, chunk_size=512, overlap=0, strategy="by_source", source="dados.csv")
    assert len(chunks) == 3
    assert chunks[0] == "linha1"

def test_by_source_csv_ignores_blank_lines():
    csv_text = "linha1\n\nlinha2\n"
    chunks = chunk_text(csv_text, chunk_size=512, overlap=0, strategy="by_source", source="dados.csv")
    assert len(chunks) == 2  # linha em branco não vira chunk

def test_by_source_txt_matches_recursive():
    text = "Paragrafo um. " * 50 + "\n\nParagrafo dois. " * 50
    a = chunk_text(text, chunk_size=128, overlap=0, strategy="by_source", source="doc.txt")
    b = chunk_text(text, chunk_size=128, overlap=0, strategy="recursive")
    assert a == b  # sem source csv, delega pro recursive sem alterar resultado

def test_by_source_no_source_falls_back_to_recursive():
    # source=None não deve quebrar nem ser tratado como csv
    text = "texto qualquer sem fonte definida " * 10
    chunks = chunk_text(text, chunk_size=128, overlap=0, strategy="by_source", source=None)
    assert len(chunks) > 0