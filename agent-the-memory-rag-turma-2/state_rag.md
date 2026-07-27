# State: implementação RAG (plano Aula 5 + Aula 6)

Última atualização: melhorias pós-revisão do plano (Blocos A, B, C concluídos).

## Onde parou

- **Fase:** Aula 6 concluída; melhorias da [docs/plan_revision.md](docs/plan_revision.md) implementadas em blocos (documentação, E2E, state).
- **Próximo passo:** Pendências futuras (re-ranking avançado, pipeline RAG configurável, híbrido/multi-query).

---

## Executado (Aula 5)

1. [x] **config/indexing.yaml** — chunking (size, overlap, strategy), csv/json/pdf, embedding, vector_store.
2. [x] **src/indexing/** — pacote completo:
   - **chunking.py** — chunk_text() com estratégias fixed e by_paragraph.
   - **loaders.py** — load_documents_from_file() para CSV, JSON, PDF (pypdf).
   - **embedding.py** — embed_texts() com Vertex AI ou mock (hash determinístico).
   - **vector_store.py** — upsert_documents() com mock em JSONL (Vertex stub para depois).
   - **__main__.py** — CLI: --config, --input, --output, --push.
3. [x] **pypdf** adicionado em pyproject.toml.
4. [x] **docs/indexing.md** — uso do CLI, config, env, assunto dos arquivos.
5. [x] **data/sample_insights.csv** e **data/sample_policies.json** — exemplos (contexto banco).
6. [x] **tests/test_indexing.py** — testes de chunking e loaders CSV/JSON.
7. [x] Validação: CLI executado com sucesso (chunks JSON e --push com mock).

## Validação do plano (Aula 5)

- **Plano:** Itens da seção "Aula 5" do plano foram implementados (config, loaders, chunking, embedding, vector_store, CLI, docs, exemplos, testes).
- **Código:** CLI executado com sucesso (`--output` e `--push`); 11 testes passando (5 indexing + 6 existentes), 2 skipped (session_gateway).
- **Arquivos criados/alterados:** config/indexing.yaml, src/indexing/*, data/sample_*.csv|json, docs/indexing.md, tests/test_indexing.py, pyproject.toml (pypdf), state_rag.md.

## Executado (Config ChromaDB + Vertex)

- [x] **config/memory_policy.yaml** — `vector_search.backend`: chroma | vertex | mock; `chroma.persist_directory`, `chroma.collection_name`; `mock.path`.
- [x] **chromadb** adicionado em pyproject.toml.
- [x] **src/indexing/vector_store.py** — carrega config, upsert para ChromaDB, Vertex (stub), mock (JSONL).
- [x] **src/memory_gateway.py** — carrega config, busca via Chroma (embed query + collection.query), Vertex ou mock.
- [x] **tests/test_memory_recall.py** — usa config temporário com backend=mock.
- [x] **docs/indexing.md** — documentado backend em memory_policy.yaml.
- Validação: CLI `--push` grava em ChromaDB; gateway com `backend: chroma` busca e retorna conteúdo indexado. Workaround NumPy 2 (np.float_) aplicado em vector_store para compatibilidade com chromadb.

## Executado (Bloco 0 — Preparação)

- [x] **docs/architecture.md** — criado com arquitetura completa melhorada (visão geral, diagrama, fluxo RAG index/query, decisões de desenho, config, testes).
- [x] **state_rag.md** — reestruturado com seção "Blocos de execução", checklist dos 7 problemas e escopo dos Blocos 1–3.

---

## Blocos de execução (~32k tokens)

Regra: ao iniciar Bloco N (N>0), carregar **apenas** state_rag.md e docs/architecture.md; implementar apenas o escopo do Bloco N; ao fim, atualizar state_rag.

### Checklist dos 7 problemas

| # | Problema | Onde | Bloco |
|---|----------|------|-------|
| 1 | Embedding da query usa RETRIEVAL_DOCUMENT | src/indexing/embedding.py | 1 |
| 2 | min_similarity_score lido mas não aplicado | src/memory_gateway.py | 1 |
| 3 | Query apenas "Sessao: {session_id}" | src/agent_router.py | 2 |
| 4 | Sem filtro por metadados no Chroma | src/memory_gateway.py | 1 |
| 5 | Resultados concatenados sem ordenar por score | src/memory_gateway.py | 1 |
| 6 | Testes: sem embedding for_query, sem Chroma+score | tests/ | 2 |
| 7 | state_rag + architecture | docs/, state_rag.md | 0 (concluído) |

### Bloco 1 — Embedding + Gateway

- **Escopo:** Problemas 1, 2, 4, 5.
- **Entregas:** `embed_texts(..., for_query=False|True)` com task_type RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY no Vertex; gateway chama `embed_texts(..., for_query=True)` na busca; Chroma: `include=["distances"]`, converter distância→similaridade, filtrar `>= min_similarity_score`, ordenar por similaridade; suportar `where_metadata` opcional em `search_customer_insights`.
- **Critério de conclusão:** pytest verde; testes existentes não podem quebrar.
- **Status:** Concluído.
- **Arquivos alterados:** src/indexing/embedding.py, src/memory_gateway.py.

### Bloco 2 — Router + Testes

- **Escopo:** Problemas 3 e 6.
- **Entregas:** agent_router monta query enriquecida (session_id + contexto da mensagem do cliente); testes: embed_texts com for_query; gateway Chroma com min_similarity; opcional E2E.
- **Critério de conclusão:** pytest verde; testes existentes não podem quebrar.
- **Status:** Concluído.
- **Arquivos alterados:** src/agent_router.py, tests/test_indexing.py, tests/test_memory_recall.py.

### Bloco 3 — Validação e docs

- **Escopo:** Validação final.
- **Entregas:** pytest verde; docs/indexing.md atualizado se necessário; state_rag com "Aula 6 concluída"; pendências futuras listadas.
- **Critério de conclusão:** pytest verde; documentação atualizada.
- **Status:** Concluído.
- **Arquivos alterados:** docs/indexing.md.

---

## Executado (Aula 6 — blocos 1–3)

- Query estruturada no agent_router (session_id + contexto da mensagem do cliente; where_metadata por session_id).
- Re-ranking/filtro por score: min_similarity_score aplicado na busca Chroma; resultados ordenados por similaridade.
- Embedding: for_query=True usa RETRIEVAL_QUERY na consulta; indexação usa RETRIEVAL_DOCUMENT.
- Testes: embed_texts (for_query True/False); gateway Chroma com min_similarity (test_ltm_gateway_chroma_min_similarity_filter).
- docs/architecture.md criado; docs/indexing.md atualizado; state_rag.md com blocos e checklist.

---

## Melhorias pós-revisão do plano (Blocos A, B, C)

Implementação das ações sugeridas em [docs/plan_revision.md](docs/plan_revision.md).

### Bloco A — Documentação

- **Escopo:** Fórmula de similaridade, comportamento quando where retorna vazio, tabela por backend (Chroma/Vertex/Mock), dimensão mock vs Vertex, critérios de conclusão por bloco.
- **Entregas:** docs/architecture.md — seção 4 (fórmula `max(0, 1 - distance)`), seção 5 (decisão where vazio, tabela backends, nota embedding); docstrings em LongTermMemoryGateway e search_customer_insights; state_rag com "Critério de conclusão" nos Blocos 1–3.
- **Status:** Concluído.
- **Arquivos alterados:** docs/architecture.md, src/memory_gateway.py, state_rag.md.

### Bloco B — Teste E2E e gateway

- **Escopo:** E2E com aceite claro; documentação Vertex/Mock no código.
- **Entregas:** test_rag_e2e_index_search_with_where (indexar CSV com session_id → buscar com where_metadata → assert conteúdo); docstrings do gateway já atualizadas no Bloco A.
- **Status:** Concluído.
- **Arquivos alterados:** tests/test_memory_recall.py.

### Bloco C — State e revisão

- **Escopo:** Atualizar state_rag e plan_revision.
- **Entregas:** state_rag com seção "Melhorias pós-revisão" e status; plan_revision com "Implementação das melhorias".
- **Status:** Concluído.
- **Arquivos alterados:** state_rag.md, docs/plan_revision.md.

---

## Pendente (pós-Aula 6)

- Re-ranking avançado (modelo de re-ranking dedicado).
- Pipeline RAG configurável (src/rag/pipeline.py).
- Híbrido, multi-query, RAG agentic, documentação adicional.
