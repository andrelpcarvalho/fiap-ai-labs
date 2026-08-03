# Setup pré-aula (PowerShell — Windows)

> **Faça isto EM CASA, antes da aula.** A instalação baixa mais de 1 GB (torch, chromadb, SDKs Google) e o modelo de embedding tem **~470 MB**. Com a turma inteira baixando ao mesmo tempo no Wi-Fi da aula, ninguém consegue trabalhar.

**Tempo estimado:** 15–30 min (dependendo da conexão)

## 1. Requisitos

- **Python 3.11 ou 3.12** (evite 3.13+ — algumas dependências pinadas podem não ter wheels e exigir compilação)
- Git
- Este guia usa **PowerShell**. Se você prefere Git Bash, siga a [versão bash](../bash/00-setup-pre-aula.md).

Verifique:

```powershell
python --version   # deve mostrar 3.11.x ou 3.12.x
git --version
```

Se `python` abrir a Microsoft Store, instale de [python.org](https://www.python.org/downloads/) marcando "Add to PATH", ou use `py -3.12` no lugar de `python`.

## 2. Clonar e criar o ambiente virtual

```powershell
git clone <url-do-repo> agent-the-memory
cd agent-the-memory
python -m venv venv
```

Ative o venv (o prompt deve mostrar `(venv)`):

```powershell
.\venv\Scripts\Activate.ps1
```

Se aparecer erro de **execution policy** ("execução de scripts foi desabilitada"), rode uma vez e ative de novo:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

## 3. Instalar as dependências

```powershell
pip install -e ".[lab]"
```

Isso instala `chromadb`, `pypdf`, `sentence-transformers` (inclui torch), `fpdf2`, `tiktoken`, `pytest`, etc. **Pode demorar vários minutos** — é normal.

## 4. Pré-baixar o modelo de embedding e o tokenizer

Rode agora para o download acontecer em casa (fica em cache; na aula nada será baixado):

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('modelo OK')"
python -c "import tiktoken; tiktoken.get_encoding('cl100k_base'); print('tiktoken OK')"
```

O primeiro comando baixa **~470 MB** do HuggingFace.

## 5. Gerar o PDF do lab e validar

```powershell
python scripts/generate_lab_pdf.py
python -c "from src.memory_gateway import LongTermMemoryGateway; print('projeto OK')"
pytest tests/test_chunking_lab.py -q
```

Esperado: `PDF gerado: ...`, `projeto OK` e todos os testes verdes.

## Checklist final

- [ ] `(venv)` aparece no prompt
- [ ] `pip install -e ".[lab]"` terminou sem erro
- [ ] Modelo e tiktoken pré-baixados (comandos do passo 4 imprimem OK)
- [ ] `data\lab\lab_conta_premium.pdf` existe
- [ ] `pytest tests/test_chunking_lab.py -q` verde

## Troubleshooting do setup

| Problema | Ação |
|----------|------|
| `python` abre a Microsoft Store | Instale de [python.org](https://www.python.org/downloads/) com "Add to PATH"; ou use `py -3.12` |
| Erro de execution policy ao ativar o venv | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` e ative de novo |
| Erro compilando `tiktoken`/`chromadb` (pede Rust/C++) | Sua versão de Python é muito nova; use 3.11 ou 3.12 |
| HTTP 429 / timeout baixando o modelo | HuggingFace limitou; aguarde alguns minutos e rode o passo 4 de novo (o download continua de onde parou) |
| Rede corporativa/proxy bloqueia HuggingFace | Rode o setup em outra rede (o cache vale depois em qualquer rede) |
| Antivírus (Defender) bloqueia/atrasa a instalação do torch | Adicione exceção para a pasta do projeto/venv ou aguarde a verificação |
| Erro de caminho longo no `pip install` | Ative long paths: `git config --global core.longpaths true` e, se preciso, habilite "Win32 long paths" no Windows |

## Pronto

Na aula, comece pelo [Lab guiado: RAG com ChromaDB](02-lab-rag-chromadb-1h.md).
