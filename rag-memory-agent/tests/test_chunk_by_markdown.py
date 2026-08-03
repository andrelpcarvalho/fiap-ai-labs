# tests/test_chunk_by_markdown.py
from scripts.chunk_by_markdown import chunk_by_markdown

MD_SAMPLE = """# Titulo Principal

## Secao A
Texto curto da secao A.

## Secao B
Texto curto da secao B.

## Secao C
Texto curto da secao C.
"""

def test_chunk_por_secao():
    chunks = chunk_by_markdown(MD_SAMPLE, max_size=200)
    assert len(chunks) == 3
    paths = {c["heading_path"] for c in chunks}
    assert paths == {
        "Titulo Principal > Secao A",
        "Titulo Principal > Secao B",
        "Titulo Principal > Secao C",
    }

def test_fallback_propaga_heading_path():
    texto_grande = "Frase numero {}. ".format(0) * 50  # forca > max_size
    md = f"# Titulo\n\n## Secao Grande\n{texto_grande}\n"
    chunks = chunk_by_markdown(md, max_size=50)
    assert len(chunks) > 1  # teve que subdividir
    assert all(c["heading_path"] == "Titulo > Secao Grande" for c in chunks)