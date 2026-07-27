# Pipeline de indexação RAG: loaders (CSV, JSON, PDF) -> chunking -> embedding -> vector store

from src.indexing.chunking import chunk_text
from src.indexing.loaders import load_documents_from_file

__all__ = ["chunk_text", "load_documents_from_file"]
