# Lab 1 — Anatomia do Chunking (versão PowerShell)

> **Shell:** PowerShell (Windows). Versão bash (Linux/macOS/Git Bash): [aqui](../bash/03-lab1-anatomia-chunking.md).

**Duração:** 45–60 min
**Nível:** sênior
**Pré-requisitos:** [setup pré-aula](00-setup-pre-aula.md) concluído; PDF do lab gerado.

## Objetivo

Entender **como** o texto vira chunks — e por que a estratégia importa — **antes** de falar de embeddings ou retrieval. Você vai medir, com os mesmos documentos, o efeito de:

- 5 estratégias: `fixed`, `by_paragraph`, `by_sentence`, `recursive` e `by_tokens` (esta última é o tema do Lab 3)
- `chunk_size` (128 / 512 / 2048)
- `overlap` (0 vs 64)

Ao final, você deve saber explicar: granularidade × contexto, por que overlap existe, e por que `recursive` costuma respeitar melhor a estrutura do documento.

## Conceito rápido (5 min)

Pipeline de indexação neste projeto:

```text
arquivo (PDF/CSV/TXT) → loader → chunk_text(strategy, size, overlap) → embedding → ChromaDB
```

Código central: [`src/indexing/chunking.py`](../../../src/indexing/chunking.py)
Config padrão: [`config/indexing.yaml`](../../../config/indexing.yaml)

| Estratégia      | Ideia                                                      | Overlap? |
|-----------------|------------------------------------------------------------|----------|
| `fixed`         | Janela deslizante de N caracteres                          | Sim      |
| `by_sentence`   | Agrupa sentenças até caber no size                         | Não      |
| `by_paragraph`  | Agrupa parágrafos (`\n\n`) até caber                       | Não      |
| `recursive`     | Quebra por parágrafo → linha → sentença → palavra          | Não*     |
| `by_tokens`     | Janela em tokens (tiktoken); detalhada no Lab 3            | Sim      |

\*A implementação atual de `recursive` não usa overlap; o parâmetro `overlap_chars` só afeta `fixed` e `by_tokens`.

## Passo 0 — Preparar

Na raiz do repositório, com o venv ativo:

```powershell
.\venv\Scripts\Activate.ps1

python scripts/generate_lab_pdf.py
ls data\lab
```

Esperado: `lab_conta_premium.pdf`, `lab_tarifas.csv`, `lab_emprestimo.txt`, `golden_set.json`.

## Passo 1 — Inspecionar um documento (10 min)

Rode o inspector no TXT de empréstimo com preview dos chunks (uma linha):

```powershell
python scripts/chunk_inspect.py --file data/lab/lab_emprestimo.txt --strategy fixed --size 128 --overlap 0 --show-chunks
```

**Observe:**

- Quantos chunks saíram?
- Quantos terminam "no meio da frase" (marcados com `✂`)?
- O significado de uma frase ficou partido entre dois chunks?

Agora repita com `recursive` e size 128:

```powershell
python scripts/chunk_inspect.py --file data/lab/lab_emprestimo.txt --strategy recursive --size 128 --show-chunks
```

**Anote:** diferença no `% mid_sentence` e na legibilidade dos trechos.

## Passo 2 — Comparar as estratégias no corpus (15 min)

```powershell
python scripts/chunk_inspect.py --compare --sizes 128 512 2048 --overlap 64
```

Você verá uma tabela com as 5 estratégias × 3 tamanhos:

```text
strategy        size    n     avg   min   max   mid%
fixed            128  ...
...
recursive        512  ...
by_tokens        512  ...
```

> Para `by_tokens`, o `size` é interpretado em **tokens** (não caracteres) — por isso os chunks dessa linha parecem "maiores" em caracteres. O Lab 3 explora isso.

### Experimentos guiados

Preencha mentalmente (ou num caderno):

1. Com **size=128**, qual estratégia gera mais chunks? Por quê?
2. Com **size=2048**, o TXT inteiro cabe em quantos chunks? Isso é bom ou ruim para retrieval?
3. Compare `fixed` size=512 overlap=64 vs overlap=0:

```powershell
python scripts/chunk_inspect.py --strategy fixed --size 512 --overlap 0
python scripts/chunk_inspect.py --strategy fixed --size 512 --overlap 64
```

O overlap **aumenta** o número de chunks. Qual o trade-off?

4. CSV: cada linha já é um "fato" curto. Rode:

```powershell
python scripts/chunk_inspect.py --file data/lab/lab_tarifas.csv --strategy fixed --size 512 --show-chunks
python scripts/chunk_inspect.py --file data/lab/lab_tarifas.csv --strategy by_paragraph --size 512 --show-chunks
```

Para CSV de tarifas, chunking agressivo ajuda ou atrapalha?

## Passo 3 — Ver o JSON do pipeline real (10 min)

Gere chunks sem push (só arquivo, uma linha):

```powershell
python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_lab1.json
```

Abra `out\chunks_lab1.json` e confira:

- `content`, `source`, `chunk_index`, `metadata.chunk_id`
- Quantos chunks por `source`?

Altere temporariamente em `config/indexing.yaml`:

```yaml
chunking:
  chunk_size_chars: 128
  overlap_chars: 0
  strategy: fixed
```

Regrave:

```powershell
python -m src.indexing --config config/indexing.yaml --input data/lab --output out/chunks_lab1_fixed128.json
```

Compare o número de registros nos dois JSONs.

> **ATENÇÃO (trabalho em grupo):** `config/indexing.yaml` é compartilhado por **todos** os labs. Se você esquecer de restaurá-lo, o lab de 1h e o Lab 2 dos colegas passam a indexar com a config errada — e ninguém percebe. Restaure **agora**:

```yaml
chunking:
  chunk_size_chars: 512
  overlap_chars: 64
  strategy: recursive
```

Confira com `git diff config/indexing.yaml` (deve estar vazio).

## Passo 4 — Discussão (10 min)

Discuta com o grupo (ou anote respostas):

1. **Granularidade × contexto:** chunk pequeno aumenta chance de achar o "fato", mas pode perder a frase que dá sentido. Chunk grande dilui a similaridade e estoura o budget de tokens do prompt.
2. **Por que overlap?** Evita perder informação que cai exatamente na fronteira entre dois chunks (ex.: "taxa a partir de" no fim de um e "0,85% a.m." no início do próximo).
3. **Por que recursive?** Documentos reais têm estrutura (parágrafos, listas). Quebrar "no meio" de um parágrafo destrói unidades semânticas; recursive tenta respeitar separadores naturais antes de forçar corte por caractere.
4. **CSV vs TXT vs PDF:** a unidade semântica muda com o formato. Um bom pipeline pode usar estratégia **por tipo de documento** (não é o default deste lab — desafio).

## Desafio extra

Implemente (ou proponha) um modo `strategy_by_source` no CLI: TXT/PDF → `recursive`, CSV → sem chunking adicional (1 chunk por linha). Não precisa mergear no main; um script paralelo em `scripts/` basta.

## Critério de conclusão

- [ ] Rodou `--compare` e entendeu a tabela
- [ ] Viu chunks com `--show-chunks` e identificou cortes ruins
- [ ] Gerou `out/chunks_lab1.json` via `python -m src.indexing`
- [ ] **Restaurou `config/indexing.yaml`** (`git diff config/indexing.yaml` vazio)
- [ ] Consegue explicar overlap e recursive em 2 minutos

## Troubleshooting

| Problema | Ação |
|----------|------|
| `chunk_inspect.py` não acha os arquivos | Rode na raiz do repositório; gere o PDF (`python scripts/generate_lab_pdf.py`) |
| `✂`/`✓` aparecem como caracteres estranhos | Encoding do console; rode `chcp 65001` ou use o Windows Terminal |
| Erro de rede em `by_tokens` no `--compare` | tiktoken baixa o encoding na 1ª vez; faltou o [setup pré-aula](00-setup-pre-aula.md) |
| Números diferentes dos colegas | Comparem o `config/indexing.yaml` — alguém pode ter esquecido de restaurar |

## Próximo

[Lab 2 — Chunking × Qualidade de Retrieval](04-lab2-chunking-retrieval.md): as mesmas configs passam a ser medidas com **hit rate@k** usando embeddings locais.
