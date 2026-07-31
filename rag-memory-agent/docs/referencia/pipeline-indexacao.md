# Pipeline de indexação RAG (Aula 5)

Pipeline **leitura → chunking → embedding → vector store** para popular a memória de longo prazo usada pelo agente (negociador de financiamento).

## Uso do CLI

```bash
# Apenas gerar chunks (JSON), sem embedding nem vector store
python -m src.indexing --config config/indexing.yaml --input data/sample_insights.csv --output out/chunks.json

# Múltiplos arquivos
python -m src.indexing -i data/sample_insights.csv data/sample_policies.json -o out/chunks.json

# Gerar chunks, embeddings e enviar ao vector store (backend definido em config/memory_policy.yaml: chroma | vertex | mock)
python -m src.indexing -i data/sample_insights.csv --output out/chunks.json --push
```

## Configuração

- **Indexação:** `config/indexing.yaml` — chunking, csv/json/pdf, embedding.
- **Vector store (backend):** `config/memory_policy.yaml` — seção `vector_search`:
  - **`backend`:** `chroma` | `vertex` | `mock` (define onde indexação grava e onde o agente busca).
  - **ChromaDB** (`backend: chroma`): `chroma.persist_directory` (ex.: `data/chroma`), `chroma.collection_name` (ex.: `customer_insights`).
  - **Vertex** (`backend: vertex`): índice e endpoint já criados no GCP; env `VECTOR_SEARCH_ENDPOINT_ID`, `VECTOR_SEARCH_INDEX_ID`, `VECTOR_SEARCH_GCS_BUCKET`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`. Opcional: `VECTOR_SEARCH_DEPLOYED_INDEX_ID`. Config `vector_search.vertex`: `index_id`, `gcs_bucket`, `deployed_index_id`, `content_store_path`, `gcs_prefix`, `is_complete_overwrite`. Indexação faz batch upsert (JSONL no GCS + update index) e grava content store local para a consulta aplicar `min_similarity_score` e ordenação (paridade com Chroma).
  - **Mock** (`backend: mock`): grava em `vector_search.mock.path` (ex.: `data/vector_store_mock.jsonl`).
- **Chunking (indexing.yaml):** `chunk_size_chars`, `overlap_chars`, `strategy` (fixed | by_paragraph)
- **CSV/JSON/PDF:** `csv.text_column`, `json.text_path`, `pdf.merge_pages`
- **Embedding:** `embedding.model`, `embedding.batch_size`; indexação usa `RETRIEVAL_DOCUMENT`, consulta usa `RETRIEVAL_QUERY` (parâmetro `for_query` em `embed_texts`).
- **Busca (memory_policy.yaml):** `max_documents`, `min_similarity_score` (documentos abaixo do score são filtrados); o agente enriquece a query com session_id e contexto da mensagem e pode filtrar por metadados (ex.: `session_id`).

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `GOOGLE_CLOUD_PROJECT` | Vertex embedding e vector store |
| `GOOGLE_CLOUD_REGION` | Região Vertex |
| `VECTOR_SEARCH_ENDPOINT_ID` | ID do Index Endpoint (Vertex Vector Search) |
| `VECTOR_SEARCH_INDEX_ID` | ID do índice (batch update) |
| `VECTOR_SEARCH_GCS_BUCKET` | Bucket GCS para upload do JSONL de batch |
| `VECTOR_SEARCH_DEPLOYED_INDEX_ID` | ID do índice implantado no endpoint (find_neighbors) |
| `INDEXING_MOCK_OUTPUT` | Caminho do arquivo mock (default: data/vector_store_mock.jsonl) |

## Assunto dos arquivos (contexto banco)

- **CSV:** insights e perfil de clientes (session_id, tier, content).
- **JSON:** políticas, regras de crédito/handoff, FAQs (content + metadados tipo, tier, vigencia).
- **PDF:** material de produto, normativo ou treinamento.

## Formato de saída (chunks)

Cada chunk é um objeto com:

- `content`: texto do chunk
- `source`: nome do arquivo de origem
- `chunk_index`: índice no documento de origem
- `metadata`: dict (session_id, tier, page, chunk_id, etc.)

## Aula 6 (concluída)

- Config no gateway: `max_documents`, `min_similarity_score` aplicados na busca Chroma; filtro por metadados (`where`) opcional.
- Query estruturada no agent_router: session_id + trecho da mensagem do cliente (até 200 caracteres).
- Embedding: task type `RETRIEVAL_DOCUMENT` na indexação e `RETRIEVAL_QUERY` na consulta.
- Ver [docs/referencia/arquitetura.md](arquitetura.md) para arquitetura completa e fluxo RAG.
