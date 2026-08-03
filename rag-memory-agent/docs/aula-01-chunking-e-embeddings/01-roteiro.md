# Roteiro — Aula 1: Conceito RAG + Chunks e Embeddings

**Público:** turma 2 (sêniores)  
**Branch:** `rag-turma-2`  
**Objetivo do dia:** explicar o conceito, fazer a turma **rodar** o projeto, e praticar **chunking** com 3 labs.

## Antes da aula (instrutor)

- [ ] Repo publicado na branch `rag-turma-2`
- [ ] **Enviar o [setup pré-aula](00-setup-pre-aula.md) para a turma com antecedência** — instalação (>1 GB) e modelo de embedding (~470 MB) devem ser baixados em casa, não no Wi-Fi da sala
- [ ] Validar em pasta limpa: clone → `pip install -e ".[lab]"` → lab 1h → Labs 1–2
- [ ] Abrir teoria: `rag.html` ou `rag_II.html` + `index.html`
- [ ] Garantir que `data/chroma`, `out/` e o PDF do lab **não** vêm populados no clone (são gerados; estão no `.gitignore`)

## Setup com a turma

Cada aluno segue o [setup pré-aula](00-setup-pre-aula.md) na versão do seu shell ([bash](bash/00-setup-pre-aula.md) para Linux/macOS/Git Bash, [PowerShell](powershell/00-setup-pre-aula.md) para Windows). Quem fez em casa só precisa ativar o venv e rodar `python scripts/generate_lab_pdf.py`.

**Não** pedir Docker nem GCP neste dia.

---

## Bloco A — Conceito (30–40 min)

Material: `rag.html` / `rag_II.html`, trechos de `index.html`.

Cobrir:

1. Problema do agente amnésico vs RAG
2. Pipeline: **chunk → embed → store → retrieve → generate**
3. Onde isso vive neste repo (`src/indexing/`, `memory_gateway`)
4. Embeddings locais vs Vertex (hoje: local)
5. Teaser: short-term (FSM) vs long-term (vector) — detalhe nas aulas seguintes

Pergunta para a sala: *“Se eu mudar só o tamanho do chunk, a resposta do agente muda?”* → gancho para os labs.

---

## Bloco B — Rodar o projeto (lab 1h) (50–60 min)

Seguir: [02-lab-rag-chromadb-1h.md](02-lab-rag-chromadb-1h.md)

Momento “aha”: mesma pergunta **antes** (vazio) e **depois** (trechos).

Se alguém travar em dependência: `pip install -e ".[lab]"` de novo; Python 3.11+.

---

## Bloco C — Labs de Chunking

Ordem sugerida (observar → medir → construir):

| Ordem | Lab | Tempo | Entrega |
|-------|-----|-------|---------|
| 1 | [Anatomia do Chunking](03-lab1-anatomia-chunking.md) | 45–60 min | Tabela `--compare` + discussão |
| 2 | [Chunking × Retrieval](04-lab2-chunking-retrieval.md) | 50–60 min | `hit rate@k` nas 4 configs |
| 3 | [Chunker by_tokens](05-lab3-chunker-por-tokens.md) | 50–60 min | pytest verde + eval |

> Cada lab tem versão **bash** (Linux/macOS/Git Bash) e **PowerShell** (Windows) — os links acima levam à página de escolha. Cada aluno segue **uma** versão do início ao fim.

### Se o tempo apertar no mesmo dia

- Faça Lab 1 **ao vivo** (instrutor + turma no `chunk_inspect.py`)
- Lab 2 como **tarefa** até a próxima aula
- Lab 3 começa na Aula 2 ou como desafio

### Se sobrar tempo

- Pegadas do lab 1h (max_documents, min_similarity)
- Desafio markdown-aware do Lab 3

---

## Arco das 3 aulas (sugestão)

| Aula | Foco | Materiais |
|------|------|-----------|
| **1 (hoje)** | Conceito + rodar + chunks/embeddings | `rag.html`, lab 1h, Labs 1–3 |
| **2** | Retrieval, similaridade, hybrid search, tuning | `hybrid_search.html`, Lab 2 revisitado |
| **3** | RAG no agente stateful (FSM + memory gateway + FinOps) | `index.html`, `python -m src.main` |

---

## Checklist de saída da Aula 1

Aluno consegue:

- [ ] Explicar o pipeline RAG deste repositório
- [ ] Rodar consulta antes/depois da indexação
- [ ] Comparar estratégias de chunking com `chunk_inspect.py`
- [ ] (ideal) Ler uma tabela de hit rate@k

Instrutor anota: quem não baixou o modelo / problemas Windows path / antivírus bloqueando torch.
