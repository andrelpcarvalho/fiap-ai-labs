# Lab 1 — Anatomia do Embedding: o que são as dimensões

**Duração:** 25 min
**Formato:** grupos de 3–4 pessoas
**Pré-requisitos:** [setup pré-aula](../aula-01-chunking-e-embeddings/00-setup-pre-aula.md) concluído (`pip install -e ".[lab]"` e modelo local baixado).

> Os comandos são idênticos em **bash e PowerShell** (tudo é `python scripts/...`). Só a ativação do venv muda:
> bash/Git Bash: `source venv/Scripts/activate` (Linux/macOS: `source venv/bin/activate`) · PowerShell: `.\venv\Scripts\Activate.ps1`

## Objetivo

Abrir a "caixa-preta": ver com os próprios olhos **o que é** um embedding (uma lista de números), o que significa a **dimensão** (384? 768?), e provar experimentalmente por que poucas dimensões não bastam para representar significado.

Ao final, cada grupo deve conseguir responder em 1 minuto: *"o que é uma dimensão de embedding e por que 384 e não 2?"*

## Papéis no grupo (troquem a cada passo)

| Papel | Faz o quê |
|-------|-----------|
| **Piloto** | Digita e roda os comandos |
| **Navegador** | Lê o roteiro em voz alta e confere a saída |
| **Apostador** | Registra as apostas do grupo ANTES de rodar e confere quem acertou |

> **Regra de ouro do lab:** toda vez que aparecer 🎲 **APOSTA**, o grupo discute e escreve a resposta **antes** de rodar o comando. Errar a aposta vale mais aprendizado que acertar.

## Conceito rápido (2 min)

Um modelo de embedding transforma texto em um **vetor**: uma lista de números que posiciona o texto em um "mapa de significados". Textos de sentido parecido ficam **próximos** nesse mapa; a **dimensão** é o número de coordenadas do mapa.

```text
"empréstimo pessoal..."  →  [ -0.02, -0.06, +0.03, ... ]   ← 384 números
                              dim 1  dim 2  dim 3 ... dim 384
```

Neste projeto (veja `config/indexing.yaml`):

| Backend | O que é | Dimensões |
|---------|---------|-----------|
| `local` | MiniLM multilíngue (sentence-transformers) — **semântico** | 384 |
| `vertex` | text-multilingual-embedding-002 (GCP) — semântico | 768 |
| `mock` | hash SHA-256 do texto — **sem semântica** (só para testes) | 768 |

## Passo 1 — Ver a cara de um embedding (5 min)

```bash
python scripts/lab_embedding_anatomia.py
```

**Observem juntos e anotem:**

1. Quantas dimensões tem o vetor?
2. Em que faixa estão os valores (perto de 0? enormes?)
3. Qual é a **norma** (comprimento) do vetor?

Testem com uma frase do próprio grupo:

```bash
python scripts/lab_embedding_anatomia.py --text "escreva qualquer frase aqui"
```

🎲 **APOSTA 1:** a norma da frase de vocês vai ser maior, menor ou igual a da frase anterior?

<details>
<summary>Gabarito do Passo 1</summary>

- **384 dimensões** (MiniLM local), valores pequenos entre ~-0.18 e +0.16.
- **Norma = 1.0000 para qualquer texto** — o pipeline normaliza os vetores (`normalize_embeddings=True` em `src/indexing/embedding.py`). Todos os textos viram pontos na superfície de uma "esfera" de raio 1; o que diferencia significado é a **direção** do vetor, não o tamanho. É por isso que a comparação usa **cosseno** (ângulo entre vetores).
- Nenhuma dimensão isolada "significa" algo legível (dim 42 ≠ "dinheiro"). O significado está espalhado pela combinação das 384.

</details>

## Passo 2 — Determinismo e sensibilidade (5 min)

🎲 **APOSTA 2:** rodando o mesmo texto duas vezes, a similaridade será exatamente 1.0? E se mudarmos **um único caractere** (`1,2%` → `1.2%`), cai para quanto? Anotem um palpite de 0 a 1 para o backend `local` e outro para o `mock`.

```bash
python scripts/lab_embedding_anatomia.py --determinismo
python scripts/lab_embedding_anatomia.py --determinismo --backend mock
```

**Comparem com as apostas.** Quem chegou mais perto?

<details>
<summary>Gabarito do Passo 2</summary>

| | mesmo texto | 1 caractere alterado |
|---|---|---|
| `local` (semântico) | 1.0000 | **≈ 0.998** — quase nada muda, porque o *significado* quase não mudou |
| `mock` (hash) | 1.0000 | **≈ 0.27** — o vetor virou outro completamente (efeito avalanche do SHA-256) |

Essa é a diferença fundamental: o hash enxerga **caracteres**, o embedding enxerga **significado**. O Lab 2 explora isso a fundo.

</details>

## Passo 3 — Dimensões incompatíveis (5 min)

```bash
python scripts/lab_embedding_anatomia.py --compare-backends
```

**Observem:** `local` = 384 dims com norma 1.0; `mock` = 768 dims com norma ~8.6. São mapas **diferentes e incomuníveis** — não existe similaridade entre um vetor de 384 e um de 768.

**Conexão com o projeto:** é por isso que o `README.md` avisa — *trocar o backend de embedding exige apagar `data/chroma` e reindexar*. A collection do ChromaDB fixa a dimensão no primeiro insert; uma query com outra dimensão gera erro. Indexar com um modelo e consultar com outro (mesmo que a dimensão bata!) produz resultados sem sentido, porque cada modelo desenha o seu próprio mapa.

## Passo 4 — Por que 384 dimensões e não 2? (8 min)

O experimento final: e se usássemos só as **primeiras k dimensões** do vetor?

🎲 **APOSTA 3:** com apenas **2 dimensões**, um sistema de busca ainda funciona? O grupo aposta SIM ou NÃO — e em qual `k` mínimo a busca fica confiável (2, 8, 32, 128?).

```bash
python scripts/lab_embedding_anatomia.py --dims-progressivas
```

O script compara 5 pares de **paráfrases** (deveriam ter similaridade ALTA) com 45 pares de frases **sem relação nenhuma** (deveriam ficar BAIXAS), usando só as primeiras k dimensões.

**Foquem na coluna `margem`:** ela é a distância entre a *pior paráfrase* e a *pior colisão acidental*. Margem **negativa** = existe um par sem relação que parece MAIS similar que uma paráfrase real → a busca retornaria lixo.

<details>
<summary>Gabarito do Passo 4 (valores medidos)</summary>

| dims | pior colisão (sem relação) | margem |
|-----:|---------------------------:|-------:|
| 2 | **1.000** | −0.231 |
| 8 | 0.847 | −0.432 |
| 16 | 0.525 | −0.087 |
| 32 | 0.408 | +0.009 |
| 128 | 0.323 | +0.178 |
| 384 | 0.322 | **+0.239** |

Com 2 dimensões, duas frases sem relação alguma colidiram com similaridade **1.000** (parecem idênticas!). A margem só fica positiva a partir de ~32 dimensões e segue melhorando até 384.

**A intuição:** em um mapa de 2 coordenadas não há "espaço" para milhões de conceitos ficarem longe uns dos outros — colisões por azar são inevitáveis. Em alta dimensão, vetores aleatórios são quase ortogonais (similaridade ≈ 0), então proximidade passa a ser um **sinal confiável** de significado compartilhado. É exatamente essa margem que o `min_similarity_score: 0.35` do `config/memory_policy.yaml` explora: acima da zona de colisão (~0.32), abaixo da zona de paráfrase.

</details>

## Discussão de fechamento (3 min)

Cada grupo responde em voz alta:

1. O que é uma dimensão de embedding? (resposta esperada: uma coordenada em um espaço onde direção ≈ significado; nenhuma dimensão tem significado isolado)
2. Por que a norma 1.0 importa? (cosseno vira comparação de ângulo; distância no Chroma é `1 − cos`)
3. Por que não dá para misturar modelos na mesma collection?

## Critério de conclusão

- [ ] Viram o vetor cru (384 valores, norma 1.0)
- [ ] Mediram: 1 caractere → local ~0.998 vs mock ~0.27
- [ ] Sabem explicar por que trocar backend exige reindexar
- [ ] Viram a colisão de 1.000 com 2 dims e a margem positiva com 384
- [ ] Fizeram as 3 apostas ANTES de rodar

## Troubleshooting

| Problema | Ação |
|----------|------|
| `ImportError: sentence_transformers` | `pip install -e ".[lab]"` na raiz do repo |
| Primeira execução lenta / baixando modelo | Normal na 1ª vez (~470 MB); faltou o setup pré-aula |
| `ModuleNotFoundError: src` | Rode na **raiz** do repositório, não dentro de `scripts/` |
| Números levemente diferentes do gabarito | Versões diferentes do modelo/lib; a *tendência* deve ser a mesma |

## Próximo

[Lab 2 — Precisão léxica × Similaridade semântica](04-lab2-lexico-vs-semantico.md): o duelo de apostas entre busca por palavras e busca por significado.
