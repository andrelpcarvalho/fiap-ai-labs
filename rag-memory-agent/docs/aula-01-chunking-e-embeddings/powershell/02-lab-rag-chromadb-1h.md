# Lab guiado: RAG com ChromaDB (1 hora) — versão PowerShell

> **Shell:** PowerShell (Windows). Versão bash (Linux/macOS/Git Bash): [aqui](../bash/02-lab-rag-chromadb-1h.md).

**Este lab usa ChromaDB local + embeddings locais** (`sentence-transformers`). Vertex AI e Docker **não** são necessários.

Você vai:

1. Fazer uma **consulta RAG** com o vector store vazio.
2. **Indexar** três arquivos (PDF, CSV e TXT) no ChromaDB.
3. Repetir a **mesma consulta** e ver o RAG retornar trechos dos documentos.
4. Entender que o **agente** já usa essa mesma base.

---

## Pré-requisitos

- **[Setup pré-aula](00-setup-pre-aula.md) concluído** (venv criado, `pip install -e ".[lab]"`, modelo pré-baixado).
- Python **3.11 ou 3.12**.
- Backend de embedding em `config/indexing.yaml`: `backend: local` (default).
- Backend do vector store em `config/memory_policy.yaml`: `backend: chroma` (default).

Se você **não** fez o setup pré-aula, a primeira indexação/consulta baixa o modelo `paraphrase-multilingual-MiniLM-L12-v2` (**~470 MB** — evite fazer isso no Wi-Fi da aula).

> **Trabalho em grupo:** se o grupo compartilha uma máquina/clone, façam os passos **juntos, em um único terminal**. Dois processos mexendo em `data\chroma` ao mesmo tempo causam erros de lock do SQLite.

---

## Cronograma (1 hora)

| Tempo | Bloco | O que fazer |
|-------|-------|-------------|
| 0–5 min | Setup | Ativar venv; gerar PDF |
| 5–10 min | Contexto | Conhecer `data\lab\` e o pipeline |
| 10–15 min | Consulta ANTES | Limpar chroma; `rag_query.py`; anotar saída vazia |
| 15–35 min | Indexação | `python -m src.indexing ... --push` |
| 35–40 min | Sistema | Agente já usa a mesma base |
| 40–55 min | Consulta DEPOIS | Mesma pergunta; comparar |
| 55–60 min | Recap | Fluxo loaders → chunks → embed → Chroma |

---

## Passo 0: Ambiente

Na **raiz do repositório** (pasta `agent-the-memory`), com o venv ativo:

```powershell
.\venv\Scripts\Activate.ps1

python -c "from src.memory_gateway import LongTermMemoryGateway; print('OK')"
python scripts/generate_lab_pdf.py
```

Confirme:

```powershell
ls scripts
ls data\lab
```

Esperado em `scripts\`: `generate_lab_pdf.py`, `rag_query.py`, `chunk_inspect.py`, `eval_retrieval.py`.
Esperado em `data\lab\`: `lab_conta_premium.pdf` (gerado acima), `lab_tarifas.csv`, `lab_emprestimo.txt` e `golden_set.json` (para os Labs 1–3).

---

## Passo 1: Arquivos do lab

| Arquivo | Formato | Conteúdo |
|---------|---------|----------|
| `lab_conta_premium.pdf` | PDF | Benefícios, tarifas, requisitos Conta Premium |
| `lab_tarifas.csv` | CSV | Tarifas (coluna `content`) |
| `lab_emprestimo.txt` | TXT | Políticas de empréstimo e handoff |

**Pergunta padrão** (use sempre a mesma):

```text
Quais são as tarifas da conta premium e as condições para empréstimo pessoal?
```

---

## Passo 2: Consulta ANTES da indexação

1. Confira `config/memory_policy.yaml`:

```yaml
vector_search:
  backend: chroma
```

2. Limpe o Chroma:

```powershell
Remove-Item -Recurse -Force data\chroma -ErrorAction SilentlyContinue
```

3. Consulte:

```powershell
python scripts/rag_query.py "Quais são as tarifas da conta premium e as condições para empréstimo pessoal?"
```

**Esperado:** `(nenhum trecho recuperado)` ou saída vazia.

---

## Passo 3: Indexar

Comando em **uma linha** (indexa a pasta `data\lab` inteira):

```powershell
python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_lab.json --push
```

Ou, listando os arquivos explicitamente:

```powershell
python -m src.indexing --config config/indexing.yaml --input data/lab/lab_conta_premium.pdf data/lab/lab_tarifas.csv data/lab/lab_emprestimo.txt --output out/chunks_lab.json --push
```

Logs esperados:

- `Chunks gravados: out/chunks_lab.json (N)`
- `Vector store ChromaDB: N documentos gravados`
- `Push concluído`

Abra `out\chunks_lab.json` e confira `content` / `source`.

> `out\` e `data\chroma\` são artefatos locais — **não commite** esses arquivos.

---

## Passo 4: O agente já usa a base

Não é necessário alterar código. O `LongTermMemoryGateway` lê o mesmo `memory_policy.yaml` e a mesma pasta `data\chroma`.

---

## Passo 5: Consulta DEPOIS

```powershell
python scripts/rag_query.py "Quais são as tarifas da conta premium e as condições para empréstimo pessoal?"
```

**Esperado:** trechos com tarifas, TEDs, taxas de empréstimo (0,85%), handoff, etc.
Compare com o Passo 2 — essa diferença é o RAG.

---

## Recap

```text
loaders (PDF/CSV/TXT) → chunking → embedding local → ChromaDB
query → embedding → busca → texto no prompt
```

Próximo na Aula 1: [Lab 1 — Anatomia do Chunking](03-lab1-anatomia-chunking.md).

---

## Troubleshooting

| Problema | Ação |
|----------|------|
| Módulo `src` não encontrado | Rode na raiz do repositório; venv ativo; `pip install -e ".[lab]"` |
| Erro de execution policy ao ativar o venv | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` e ative de novo |
| RAG vazio após indexar | `backend: chroma` em `memory_policy.yaml`; confira o log "N documentos gravados"; alguém mudou `config/indexing.yaml` (Labs 1/3)? Restaure `strategy: recursive`, `512`, `64` e reindexe |
| `Remove-Item` falha ("arquivo em uso") | Outro processo Python segura o SQLite do Chroma; feche os demais terminais do grupo e tente de novo |
| Dimensão incompatível | Apague `data\chroma` e reindexe (acontece ao trocar local↔vertex↔mock) |
| HTTP 429 / erro baixando modelo | Faltou o [setup pré-aula](00-setup-pre-aula.md); aguarde e tente de novo, ou use `--backend mock` só para validar o fluxo |
| `sentence-transformers` / torch lento | Normal na 1ª carga do modelo em memória; depois fica em cache |
| Warnings "Failed to send telemetry" do Chroma | Inofensivo; ignore |
| Quer só smoke sem baixar modelo | `embedding.backend: mock` em `indexing.yaml` (semântica fraca) |

---

## Validação rápida (instrutor)

1. `python scripts/generate_lab_pdf.py`
2. `Remove-Item -Recurse -Force data\chroma`; `python scripts/rag_query.py "..."` → vazio
3. Indexar com `--push` → N docs
4. Mesma query → trechos
5. `pytest tests/ -v` → verde
