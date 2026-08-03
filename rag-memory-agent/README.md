# Agente 3: The Memory (RAG — Turma 2)

Projeto didático para ensino de **RAG** (Retrieval-Augmented Generation) e agentes stateful: chunking, embeddings, ChromaDB local e memória de longo prazo com Google ADK.

**Branch recomendada para a turma:** `rag-turma-2`

## Pré-requisitos

| Item | Obrigatório? | Notas |
|------|--------------|--------|
| Git | Sim | Para clonar o repositório |
| Python **3.11 ou 3.12** | Sim | `python --version` (evite 3.13+: dependências pinadas podem exigir compilação) |
| Rede (1ª vez) | Sim | Instalação (>1 GB) + modelo de embedding local (~470 MB) — **faça em casa, antes da aula** |
| Docker | **Não** | Opcional; só para rodar o agente containerizado |
| Conta GCP / Vertex AI | **Não** | Opcional; default usa embeddings locais |
| API Key Google AI | Só se for rodar o **agente** conversacional | Labs de chunking/RAG funcionam sem |

> **Alunos:** sigam o [setup pré-aula](docs/aula-01-chunking-e-embeddings/00-setup-pre-aula.md), que tem versão **bash** (Linux/macOS/Git Bash) e **PowerShell** (Windows) com todos os passos e o pré-download do modelo.

## Instalação rápida (labs de RAG)

```bash
git clone <url-do-repo> agent-the-memory
cd agent-the-memory
git checkout rag-turma-2

python -m venv venv
# Windows (PowerShell):
#   .\venv\Scripts\Activate.ps1
# Windows (Git Bash):
#   source venv/Scripts/activate
# Linux/macOS:
#   source venv/bin/activate

pip install -e ".[lab]"
```

O extra `[lab]` inclui `sentence-transformers` (embeddings locais) e `fpdf2` (gerar PDF do lab).

Verifique:

```bash
python -c "from src.indexing.chunking import chunk_text; from src.indexing.embedding import embed_texts; print('OK')"
pytest tests/ -v
```

## Configuração de embeddings

Em [`config/indexing.yaml`](config/indexing.yaml):

```yaml
embedding:
  backend: local   # local | vertex | mock
  model: paraphrase-multilingual-MiniLM-L12-v2
```

| Backend | Quando usar |
|---------|-------------|
| `local` | **Default da turma** — semântico, offline após download |
| `vertex` | Com `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` |
| `mock` | CI / smoke (hash; **sem** semântica real) |

**Importante:** trocar de backend muda a dimensão do vetor. Apague `data/chroma` e reindexe.

## Lab guiado (1 hora) — ciclo RAG completo

Passo a passo: [docs/aula-01-chunking-e-embeddings/02-lab-rag-chromadb-1h.md](docs/aula-01-chunking-e-embeddings/02-lab-rag-chromadb-1h.md)

Resumo:

```bash
python scripts/generate_lab_pdf.py
python scripts/rag_query.py "Quais são as tarifas da conta premium e as condições para empréstimo pessoal?"
# (vazio se chroma limpo)

python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_lab.json --push

python scripts/rag_query.py "Quais são as tarifas da conta premium e as condições para empréstimo pessoal?"
# (trechos dos documentos)
```

## Labs de Chunking (Aula 1)

| Lab | Tema | Doc |
|-----|------|-----|
| 1 | Anatomia do chunking (estratégias, size, overlap) | [docs/aula-01-chunking-e-embeddings/03-lab1-anatomia-chunking.md](docs/aula-01-chunking-e-embeddings/03-lab1-anatomia-chunking.md) |
| 2 | Chunking × qualidade de retrieval (hit rate@k) | [docs/aula-01-chunking-e-embeddings/04-lab2-chunking-retrieval.md](docs/aula-01-chunking-e-embeddings/04-lab2-chunking-retrieval.md) |
| 3 | Chunker próprio `by_tokens` (tiktoken) | [docs/aula-01-chunking-e-embeddings/05-lab3-chunker-por-tokens.md](docs/aula-01-chunking-e-embeddings/05-lab3-chunker-por-tokens.md) |

Cada lab tem versão **bash** e **PowerShell** (os links levam à página de escolha).

Roteiro da aula: [docs/aula-01-chunking-e-embeddings/01-roteiro.md](docs/aula-01-chunking-e-embeddings/01-roteiro.md)

Índice completo da documentação (aulas 1–3, referência e material do professor): [docs/README.md](docs/README.md)

## Arquitetura (visão rápida)

```text
Indexação:  loaders → chunking → embedding → ChromaDB (data/chroma)
Consulta:   query → embedding → Chroma top-k → texto no prompt do agente
```

- Short-term memory: Session Gateway (FSM)
- Long-term memory: [`src/memory_gateway.py`](src/memory_gateway.py) + Chroma

## Docker (opcional)

Só necessário se quiser subir o **agente** em container (não os labs de chunking):

```bash
# .env com GOOGLE_API_KEY ou variáveis Vertex
docker compose up --build
```

O ChromaDB do lab é **embedded** (pasta local); não há serviço Docker de vector DB.

## Vertex / Google AI (opcional — agente)

### Opção A – Google AI (API Key)

```bash
export GOOGLE_API_KEY="sua-api-key"
```

### Opção B – Vertex AI

```bash
gcloud auth application-default login
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT="seu-projeto"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Execução do agente e testes

```bash
python -m src.main
pytest tests/ -v
```

## Materiais de teoria (HTML)

- `index.html` — arquitetura de agentes / memória
- `rag.html` / `rag_II.html` — RAG
- `hybrid_search.html` — hybrid search (Aula 2)

## Troubleshooting rápido

| Problema | Ação |
|----------|------|
| `chromadb` / `pypdf` não encontrado | `pip install -e ".[lab]"` na raiz |
| Consulta vazia após indexar | `backend: chroma` em `config/memory_policy.yaml`; confira `data/chroma` |
| Dimensão incompatível no Chroma | Apague `data/chroma` e reindexe após trocar embedding backend |
| Erro ao abrir `data/chroma` criado com chromadb 0.5.x | Apague `data/chroma` e reindexe (o projeto agora usa chromadb 1.x) |
| Embeddings mock na mensagem de log | Instale `[lab]` ou defina `embedding.backend: local` |
