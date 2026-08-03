# Lab 2 — Chunking × Qualidade de Retrieval (versão bash)

> **Shell:** bash (Linux, macOS ou Git Bash no Windows). Versão PowerShell: [aqui](../powershell/04-lab2-chunking-retrieval.md).

**Duração:** 50–60 min
**Nível:** sênior
**Pré-requisitos:** Lab 1 concluído; [setup pré-aula](00-setup-pre-aula.md) (embeddings locais).

## Objetivo

Medir, com evidência, como a configuração de chunking afeta o **retrieval**.
Você vai indexar o mesmo corpus sob 4 configs, consultar um **golden set** de 10 perguntas e comparar **hit rate@k**.

Definição de *hit*: entre os top-k chunks retornados, pelo menos um contém a string esperada (`must_contain` em [`data/lab/golden_set.json`](../../../data/lab/golden_set.json)).

## Por que isso importa

No Lab 1 você *observou* chunks. Aqui você *mede* impacto no sistema:

```text
pergunta → embedding(query) → Chroma top-k → o fato está no contexto?
```

Se o chunk cortou "0,85% a.m." longe de "cliente premium", a pergunta pode falhar mesmo com embedding bom.

## Configs avaliadas (default)

| Nome              | strategy   | size | overlap |
|-------------------|------------|------|---------|
| `fixed_128_o0`    | fixed      | 128  | 0       |
| `fixed_512_o64`   | fixed      | 512  | 64      |
| `recursive_512`   | recursive  | 512  | 0       |
| `by_tokens_128`   | by_tokens  | 128 tokens | 16 tokens |

> `by_tokens_128` usa a estratégia por tokens que você vai estudar a fundo no **Lab 3** (a implementação já existe no repositório). Aqui ela entra só como mais um ponto de comparação.

Coleções Chroma **separadas** em `data/chroma_lab2/` (não mistura com `data/chroma` do lab de 1h).

## Passo 0 — Ambiente

Na raiz do repositório, com o venv ativo:

```bash
python scripts/generate_lab_pdf.py
```

Se você fez o [setup pré-aula](00-setup-pre-aula.md), o modelo de embedding já está em cache e **nada será baixado**. (Sem o setup, a primeira execução baixa ~470 MB.)

## Passo 1 — Conhecer o golden set (5 min)

Abra [`data/lab/golden_set.json`](../../../data/lab/golden_set.json). Exemplos:

- Taxa premium `0,85%`
- Handoff após `3 recusas`
- Segunda via `R$ 35`
- Renda mínima Conta Premium

**Exercício:** escolha 2 perguntas e localize manualmente a resposta nos arquivos de `data/lab/`. Anote se a resposta está no meio de um parágrafo longo.

## Passo 2 — Rodar a avaliação (15 min)

```bash
python scripts/eval_retrieval.py --clean --verbose
```

Saída esperada (números aproximados; dependem do modelo):

```text
Backend embedding: local
...
config             chunks   hits   hit@3
----------------------------------------------
fixed_128_o0          ..    x/10    ..%
fixed_512_o64         ..    x/10    ..%
recursive_512         ..    x/10    ..%
by_tokens_128         ..    x/10    ..%
```

Com `--verbose`, cada pergunta mostra `OK` ou `MISS` e um preview do melhor chunk.

Resumo também em `out/lab2_eval.json`.

### Se `sentence-transformers` falhar

```bash
python scripts/eval_retrieval.py --backend mock --clean
```

O mock **não** é semântico: use só para validar o script; os hits serão ruins/aleatórios.

## Passo 3 — Experimentos guiados (20 min)

1. **Chunk pequeno vs recursive:**

```bash
python scripts/eval_retrieval.py --configs fixed_128_o0 recursive_512 --verbose
```

Compare quais `id` (q01…q10) falham em cada uma. Neste corpus pequeno, com fatos curtos, o chunk de 128 pode até ganhar — discuta por que isso **não** generaliza para documentos longos.

2. **Variar k:**

```bash
python scripts/eval_retrieval.py --k 1 --clean
python scripts/eval_retrieval.py --k 5
```

hit@1 costuma cair; hit@5 sobe — mas no agente, k alto = mais tokens e mais ruído no prompt.

3. **Variar min_sim:**

```bash
python scripts/eval_retrieval.py --min-sim 0.05 --verbose
python scripts/eval_retrieval.py --min-sim 0.50 --verbose
```

Threshold alto = menos falso positivo, mais MISS. Relacione com `min_similarity_score` em [`config/memory_policy.yaml`](../../../config/memory_policy.yaml).

4. **Pergunta adversária (manual):** invente uma pergunta cujo fato está no PDF, rode:

```bash
python scripts/rag_query.py "Qual a renda mínima da Conta Premium?"
```

(isso usa `data/chroma` do lab de 1h — indexe antes se ainda não o fez.)

## Passo 4 — Discussão (10 min)

1. **Chunk pequeno (128):** tende a isolar o "fato" (número), mas perde contexto ("para quem?"). Embedding da query pode não casar com um fragmento truncado.
2. **Chunk grande / recursive:** mais contexto por chunk; similaridade média pode cair se o chunk misturar vários assuntos.
3. **Overlap:** recupera fatos na fronteira; custo = mais chunks e mais armazenamento.
4. **Chars vs tokens:** `by_tokens_128` corta pelo mesmo critério que o modelo "enxerga" — compare os MISS dela com `fixed_128_o0`.
5. **Efeito no agente:** o `LongTermMemoryGateway` concatena top-k no prompt. Mais hits ≠ melhor resposta se o contexto for barulhento (FinOps + qualidade).

## Desafio extra

1. Adicione 2 perguntas ao `golden_set.json` (uma fácil, uma que exige cruzar CSV + TXT). Dica: use agulhas específicas (`"3 recusas"`, não `"3"`) — substring curta casa com qualquer chunk numérico e infla o hit rate.
2. Rode de novo e veja se alguma config degrada.
3. (Opcional) Adicione uma 5ª config ao `DEFAULT_CONFIGS` de `scripts/eval_retrieval.py` — por exemplo `by_tokens_256` ou `by_paragraph_512` — e compare.

## Critério de conclusão

- [ ] Rodou `eval_retrieval.py --clean --verbose` com backend local
- [ ] Explicou pelo menos 1 MISS olhando o chunk retornado
- [ ] Variou `k` ou `min_sim` e descreveu o efeito
- [ ] Entende por que medir hit rate antes de "tunar o prompt do agente"

## Troubleshooting

| Problema | Ação |
|----------|------|
| Download do modelo no meio da aula | Faltou o [setup pré-aula](00-setup-pre-aula.md); enquanto baixa, valide o fluxo com `--backend mock` |
| Hit rates todos iguais/estranhos | Alguém alterou `config/indexing.yaml`? Este script **não** usa o YAML (configs são internas), então confira se você não está olhando `out/chunks_lab.json` de outro lab |
| Erro de lock/permissão em `data/chroma_lab2` | Feche outros processos Python do grupo e rode com `--clean` |
| Warnings "Failed to send telemetry" | Inofensivo; ignore |

## Próximo

[Lab 3 — Construa seu próprio Chunker](05-lab3-chunker-por-tokens.md): reimplementar `by_tokens` com tiktoken e reavaliar.
