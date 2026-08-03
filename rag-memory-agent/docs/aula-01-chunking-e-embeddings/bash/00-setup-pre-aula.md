# Setup pré-aula (bash — Linux, macOS e Git Bash no Windows)

> **Faça isto EM CASA, antes da aula.** A instalação baixa mais de 1 GB (torch, chromadb, SDKs Google) e o modelo de embedding tem **~470 MB**. Com a turma inteira baixando ao mesmo tempo no Wi-Fi da aula, ninguém consegue trabalhar.

**Tempo estimado:** 15–30 min (dependendo da conexão)

## 1. Requisitos

- **Python 3.11 ou 3.12** (evite 3.13+ — algumas dependências pinadas podem não ter wheels e exigir compilação)
- Git
- No Windows: use o **Git Bash** para este guia. Se preferir PowerShell, siga a [versão PowerShell](../powershell/00-setup-pre-aula.md).

Verifique:

```bash
python --version   # deve mostrar 3.11.x ou 3.12.x
git --version
```

Se `python` não existir, tente `python3` (e use `python3` nos demais comandos).

## 2. Clonar e criar o ambiente virtual

```bash
git clone <url-do-repo> agent-the-memory
cd agent-the-memory
python -m venv venv
```

Ative o venv (o prompt deve mostrar `(venv)`):

```bash
# Linux/macOS
source venv/bin/activate

# Git Bash no Windows
source venv/Scripts/activate
```

## 3. Instalar as dependências

```bash
pip install -e ".[lab]"
```

Isso instala `chromadb`, `pypdf`, `sentence-transformers` (inclui torch), `fpdf2`, `tiktoken`, `pytest`, etc. **Pode demorar vários minutos** — é normal.

## 4. Pré-baixar o modelo de embedding e o tokenizer

Rode agora para o download acontecer em casa (fica em cache; na aula nada será baixado):

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('modelo OK')"
python -c "import tiktoken; tiktoken.get_encoding('cl100k_base'); print('tiktoken OK')"
```

O primeiro comando baixa **~470 MB** do HuggingFace.

## 5. Gerar o PDF do lab e validar

```bash
python scripts/generate_lab_pdf.py
python -c "from src.memory_gateway import LongTermMemoryGateway; print('projeto OK')"
pytest tests/test_chunking_lab.py -q
```

Esperado: `PDF gerado: ...`, `projeto OK` e todos os testes verdes.

## Checklist final

- [ ] `(venv)` aparece no prompt
- [ ] `pip install -e ".[lab]"` terminou sem erro
- [ ] Modelo e tiktoken pré-baixados (comandos do passo 4 imprimem OK)
- [ ] `data/lab/lab_conta_premium.pdf` existe
- [ ] `pytest tests/test_chunking_lab.py -q` verde

## Troubleshooting do setup

| Problema | Ação |
|----------|------|
| `python` abre a Microsoft Store (Windows) | Instale Python de [python.org](https://www.python.org/downloads/) e marque "Add to PATH"; ou use `py -3.12` |
| Erro compilando `tiktoken`/`chromadb` (pede Rust/C++) | Sua versão de Python é muito nova; use 3.11 ou 3.12 |
| HTTP 429 / timeout baixando o modelo | HuggingFace limitou; aguarde alguns minutos e rode o passo 4 de novo (o download continua de onde parou) |
| Rede corporativa/proxy bloqueia HuggingFace | Rode o setup em outra rede (o cache vale depois em qualquer rede) |
| Antivírus bloqueia/atrasa a instalação do torch | Adicione exceção para a pasta do projeto/venv ou aguarde a verificação |
| `pip install` muito lento | Normal na primeira vez (>1 GB); não cancele |

## Pronto

Na aula, comece pelo [Lab guiado: RAG com ChromaDB](02-lab-rag-chromadb-1h.md).
