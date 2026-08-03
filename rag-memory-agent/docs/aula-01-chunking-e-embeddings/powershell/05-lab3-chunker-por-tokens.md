# Lab 3 — Construa seu próprio Chunker `by_tokens` (versão PowerShell)

> **Shell:** PowerShell (Windows). Versão bash (Linux/macOS/Git Bash): [aqui](../bash/05-lab3-chunker-por-tokens.md).

**Duração:** 50–60 min
**Nível:** sênior
**Pré-requisitos:** Labs 1 e 2; `tiktoken` já está nas dependências do projeto.

## Objetivo

Implementar (ou reimplementar e validar) a estratégia **`by_tokens`** em [`src/indexing/chunking.py`](../../../src/indexing/chunking.py):

- Chunk por **número de tokens** (não caracteres), com overlap em tokens
- Encoding: `cl100k_base` (mesma família GPT/muitos embeddings)
- Plugar via `strategy: by_tokens` no YAML
- Cobrir com testes pytest
- Reavaliar com o script do Lab 2

### Por que tokens?

Modelos de embedding e LLMs têm limites em **tokens**, não em caracteres. Um chunk de 512 caracteres em português pode ter ~120–180 tokens; em código ou inglês, a relação muda. Chunking por tokens alinha o pipeline ao custo e ao limite real da API.

## Especificação

```python
def _chunk_by_tokens(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """
    - Encode com tiktoken.get_encoding("cl100k_base")
    - Janela de `chunk_size` tokens, avanço de (chunk_size - overlap)
    - Decode de cada janela → string stripada
    - overlap = min(max(0, overlap), chunk_size - 1)
    - Texto vazio → []
    """
```

Integração em `chunk_text`:

```python
if strategy == "by_tokens":
    return _chunk_by_tokens(text, chunk_size, overlap)
```

Neste repositório a implementação **já está presente** (para o instrutor validar a aula). Seu trabalho neste lab:

1. **Ler** a implementação atual e explicar linha a linha
2. **Apagar temporariamente** `_chunk_by_tokens` e o branch em `chunk_text`, e **reimplementar do zero**
3. Comparar com a solução de referência em [`solucoes/lab3_by_tokens.py`](../solucoes/lab3_by_tokens.py)
4. Rodar os testes e o eval do Lab 2

## Passo 1 — Testes primeiro (15 min)

Abra [`tests/test_chunking_lab.py`](../../../tests/test_chunking_lab.py). Rode:

```powershell
pytest tests/test_chunking_lab.py -v
```

Se a implementação estiver correta, tudo passa.
Agora **comente** o corpo de `_chunk_by_tokens` e faça-o `raise NotImplementedError` — os testes devem falhar. Reimplemente até verde.

Casos cobertos pelo esqueleto:

- texto vazio
- chunk_size em tokens respeitado (encode → len ≤ size)
- overlap produz mais chunks que sem overlap
- strategy despacha corretamente

## Passo 2 — Implementação (20 min)

1. Importe `tiktoken` só dentro de `_chunk_by_tokens` (lazy import, como no restante do projeto).
2. Encode → slice → decode.
3. Cuidado com `overlap >= chunk_size` (clamp).
4. Não esqueça `strip()` e pular peças vazias.

Checklist mental:

- [ ] Encoding `cl100k_base`
- [ ] Loop `while start < len(tokens)`
- [ ] `end = min(start + chunk_size, len(tokens))`
- [ ] Avanço `start = end - overlap` (ou `end` se overlap 0)
- [ ] Break quando `end >= len(tokens)`

## Passo 3 — Config e indexação (10 min)

Primeiro, inspecione os chunks por tokens (sem mexer em config, uma linha):

```powershell
python scripts/chunk_inspect.py --file data/lab/lab_emprestimo.txt --strategy by_tokens --size 64 --overlap 8 --show-chunks
```

Compare com as demais estratégias em tamanhos pequenos (em `--compare`, o `--strategy` é ignorado — a tabela roda todas):

```powershell
python scripts/chunk_inspect.py --compare --sizes 64 128 --overlap 8
```

Agora altere `config/indexing.yaml`:

```yaml
chunking:
  chunk_size_chars: 128   # aqui: número de TOKENS quando strategy=by_tokens
  overlap_chars: 16
  strategy: by_tokens
```

> O nome do campo ainda é `chunk_size_chars` por legado do YAML — com `by_tokens`, interprete como tokens. (Desafio de limpeza: renomear para `chunk_size` no futuro.)

Indexe (coleção principal do lab):

```powershell
# limpe o chroma do lab de 1h
Remove-Item -Recurse -Force data\chroma -ErrorAction SilentlyContinue

python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_by_tokens.json --push
```

## Passo 4 — Reavaliar com Lab 2 (10 min)

A config `by_tokens_128` **já está** em `DEFAULT_CONFIGS` de `scripts/eval_retrieval.py` — agora que você reimplementou a estratégia, é ela que está sendo medida. Rode:

```powershell
python scripts/eval_retrieval.py --configs by_tokens_128 recursive_512 --clean --verbose
```

Compare hit rate. Tokens vs caracteres: quem ganha neste corpus pequeno?

> **ATENÇÃO (trabalho em grupo):** restaure `config/indexing.yaml` para `recursive` / 512 / 64 **agora**, e reindexe `data\chroma` se seus colegas ainda vão rodar o lab de 1h nesta máquina:

```powershell
python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_lab.json --push
```

Confira com `git diff config/indexing.yaml` (deve estar vazio) e `git diff src/indexing/chunking.py` (sua reimplementação deve ser equivalente à original).

## Discussão

1. Por que `cl100k_base` e não contar palavras?
2. Um modelo de embedding com max 256 tokens — qual `chunk_size` você escolheria e por quê?
3. Overlap em tokens vs overlap em chars: qual é mais previsível para FinOps?

## Desafio extra — Markdown-aware

Implemente `strategy: by_markdown` (arquivo novo ou branch):

- Quebrar por headers `#` / `##` / `###`
- Cada chunk carrega metadata `heading_path` (ex.: `"Políticas > Handoff"`)
- Teste com um `.md` sintético em `data\lab\`

Não precisa integrar ao Chroma; valide com `chunk_inspect` ou um script próprio.

## Critério de conclusão

- [ ] `pytest tests/test_chunking_lab.py -v` verde
- [ ] Reimplementou `by_tokens` sem colar cegamente
- [ ] Indexou com `strategy: by_tokens` e gerou JSON
- [ ] Comparou hit rate com `recursive_512`
- [ ] **Restaurou `config/indexing.yaml`** e reindexou o `data\chroma` padrão

## Troubleshooting

| Problema | Ação |
|----------|------|
| Erro de rede no tiktoken | O encoding `cl100k_base` é baixado na 1ª vez; faltou o [setup pré-aula](00-setup-pre-aula.md) |
| `Remove-Item` em `data\chroma` falha ("arquivo em uso") | Outro processo Python segura o SQLite; feche os demais terminais do grupo e tente de novo |
| Testes passam mas eval estranho | Confira se o branch `by_tokens` em `chunk_text` foi religado após a reimplementação |

## Referências

- Solução: [`solucoes/lab3_by_tokens.py`](../solucoes/lab3_by_tokens.py)
- [tiktoken](https://github.com/openai/tiktoken)
- Lab 2: [`04-lab2-chunking-retrieval.md`](04-lab2-chunking-retrieval.md)
