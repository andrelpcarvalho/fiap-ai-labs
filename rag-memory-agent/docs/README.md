# Documentação — Agente 3: The Memory (RAG)

Material organizado em **3 aulas** (arco sugerido no roteiro da Aula 1), além de referência técnica e material do professor.

## Aula 1 — Conceito RAG, Chunking e Embeddings

> Foco: entender o pipeline RAG, rodar o projeto do zero e praticar chunking.

| # | Arquivo | Conteúdo | Duração |
|---|---------|----------|---------|
| 0 | [00-setup-pre-aula.md](aula-01-chunking-e-embeddings/00-setup-pre-aula.md) | **Setup pré-aula** (fazer em casa): instalação e pré-download do modelo | 15–30 min |
| 1 | [01-roteiro.md](aula-01-chunking-e-embeddings/01-roteiro.md) | Roteiro da aula (blocos A/B/C, checklist do instrutor) | — |
| 2 | [02-lab-rag-chromadb-1h.md](aula-01-chunking-e-embeddings/02-lab-rag-chromadb-1h.md) | Lab guiado: ciclo RAG completo com ChromaDB local (antes/depois da indexação) | 1h |
| 3 | [03-lab1-anatomia-chunking.md](aula-01-chunking-e-embeddings/03-lab1-anatomia-chunking.md) | Lab 1: estratégias de chunking, chunk_size e overlap | 45–60 min |
| 4 | [04-lab2-chunking-retrieval.md](aula-01-chunking-e-embeddings/04-lab2-chunking-retrieval.md) | Lab 2: impacto do chunking na qualidade do retrieval (hit rate@k) | 50–60 min |
| 5 | [05-lab3-chunker-por-tokens.md](aula-01-chunking-e-embeddings/05-lab3-chunker-por-tokens.md) | Lab 3: implementar chunker `by_tokens` com tiktoken (solução em `solucoes/`) | 50–60 min |

> O setup e cada lab da Aula 1 existem em **duas versões** — [`bash/`](aula-01-chunking-e-embeddings/bash/) (Linux, macOS, Git Bash) e [`powershell/`](aula-01-chunking-e-embeddings/powershell/) (Windows) — que diferem apenas nos comandos de terminal. Os links acima levam à página de escolha.

## Aula 2 — Retrieval, Memória de Longo Prazo e Vector Search

> Foco: aprofundar o fluxo de consulta (similaridade, filtros) e levar o vector store para a nuvem (Vertex AI).

| # | Arquivo | Conteúdo |
|---|---------|----------|
| 1 | [01-tutorial-rag-memoria-longo-prazo.md](aula-02-retrieval-e-vector-search/01-tutorial-rag-memoria-longo-prazo.md) | Tutorial completo: chunks → embedding → vector store → consulta, arquivo por arquivo |
| 2 | [02-tutorial-vertex-vector-search.md](aula-02-retrieval-e-vector-search/02-tutorial-vertex-vector-search.md) | Vertex AI Vector Search do zero: bucket, índice, endpoint e deploy no GCP |

## Aula 3 — Agente Stateful (FSM, Gateways e FinOps)

> Foco: o RAG dentro do agente de negociação com memória de curto e longo prazo.

| # | Arquivo | Conteúdo |
|---|---------|----------|
| 1 | [01-teoria-agente-the-memory.md](aula-03-agente-stateful/01-teoria-agente-the-memory.md) | Teoria: agente amnésico, arquitetura de memória, FSM, OCC, FinOps |
| 2 | [02-lab-deteccao-recusa-llm.md](aula-03-agente-stateful/02-lab-deteccao-recusa-llm.md) | Lab guiado: detecção de recusa via structured output e FSM condicional |

## Referência técnica

| Arquivo | Conteúdo |
|---------|----------|
| [referencia/arquitetura.md](referencia/arquitetura.md) | Arquitetura do sistema, fluxos RAG de indexação/consulta, decisões de desenho |
| [referencia/pipeline-indexacao.md](referencia/pipeline-indexacao.md) | CLI de indexação, configuração e variáveis de ambiente |

## Material do professor

| Arquivo | Conteúdo |
|---------|----------|
| [professor/guia-do-professor.md](professor/guia-do-professor.md) | Explicação arquivo por arquivo, na ordem das dependências, para conduzir a aula |
| [professor/revisao-plano-rag.md](professor/revisao-plano-rag.md) | Revisão crítica do plano de implementação do RAG (documento interno) |

## Materiais de teoria (HTML, na raiz do repo)

- `index.html` — arquitetura de agentes / memória
- `rag.html`, `rag_II.html`, `rag_agentic.html` — teoria de RAG
- `hybrid_search.html` — hybrid search (Aula 2)
