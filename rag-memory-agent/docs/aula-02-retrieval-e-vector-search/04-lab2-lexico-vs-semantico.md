# Lab 2 — Precisão léxica × Similaridade semântica: o Duelo

**Duração:** 35 min
**Formato:** grupos de 3–4 pessoas, com placar entre grupos
**Pré-requisitos:** [Lab 1 — Anatomia do Embedding](03-lab1-anatomia-do-embedding.md) concluído.

> Os comandos são idênticos em **bash e PowerShell** (tudo é `python scripts/...`).

## Objetivo

Entender **quando busca por palavras (léxica) acerta e quando falha**, e o que a similaridade semântica resolve — e o que ela **não** resolve. Tudo por medição, apostando antes de ver o resultado.

Três "juízes" avaliam cada par de frases:

| Juiz | Como decide | Escala |
|------|-------------|--------|
| **Léxico** (Jaccard) | palavras em comum ÷ palavras totais | 0 a 1 |
| **Hash** (mock SHA-256) | cosseno de vetores derivados dos caracteres | ~-0.3 a 1 |
| **Semântico** (MiniLM local) | cosseno dos embeddings — ângulo entre significados | ~0 a 1 |

## Passo 1 — Fase de apostas (8 min)

Vejam os 6 pares **sem os scores**:

```bash
python scripts/lab_lexico_vs_semantico.py --apostas
```

O Apostador desenha esta tabela e o grupo preenche **ALTO** (> 0.5) ou **BAIXO** (< 0.5) para cada célula — 12 apostas no total:

| Par | Léxico: ALTO/BAIXO? | Semântico: ALTO/BAIXO? |
|-----|---------------------|------------------------|
| P1 paráfrase (outras palavras) | | |
| P2 mesmas palavras, sentido invertido | | |
| P3 erro de digitação (1 acento) | | |
| P4 mesmo vocabulário, pergunta diferente | | |
| P5 idiomas diferentes, mesmo sentido | | |
| P6 sem relação nenhuma | | |

> Dica de discussão: para cada par, perguntem primeiro *"quantas palavras eles compartilham?"* (prevê o léxico) e depois *"eles querem dizer a mesma coisa?"* (prevê o semântico).

## Passo 2 — Revelação e placar (7 min)

```bash
python scripts/lab_lexico_vs_semantico.py
```

**1 ponto por célula acertada (máx. 12). Anunciem o placar entre os grupos.**

<details>
<summary>Gabarito (valores medidos) — abrir só depois de apostar!</summary>

| Par | léxico | hash | semântico |
|-----|-------:|-----:|----------:|
| P1 paráfrase | **0.00** | −0.03 | **0.73** |
| P2 sentido invertido | **1.00** | −0.03 | **0.99** |
| P3 erro de digitação | 0.67 | −0.21 | **0.98** |
| P4 mesmo vocabulário, outra pergunta | 0.50 | −0.29 | 0.62 |
| P5 idiomas diferentes | **0.00** | 0.15 | **0.98** |
| P6 sem relação | 0.00 | 0.31 | 0.02 |

</details>

**Discutam os 3 resultados mais importantes:**

1. **P1 (paráfrase):** léxico deu **0.00** — nenhuma palavra em comum — mas o sentido é o mesmo (semântico 0.73). *Esse é o caso que justifica RAG com embeddings*: o cliente nunca pergunta com as palavras do documento.
2. **P5 (idiomas):** léxico 0.00, semântico **0.98**. O modelo é multilíngue: português e inglês caem no mesmo ponto do mapa de significados. Nenhuma busca por palavra-chave faz isso.
3. **P2 (sentido invertido) — a pegadinha do lab:** "o cliente recusou o banco" vs "o banco recusou o cliente". Léxico dá **1.00** (mesmas palavras!) e o semântico dá **0.99** — *os dois juízes foram enganados*. Embeddings de sentença funcionam como um "saco de significados": capturam o assunto, mas são fracos com **ordem e papéis** (quem fez o quê a quem). Limitação real de sistemas RAG em produção.

E o juiz **hash**? Notem que os valores dele são ruído (−0.29 a 0.31) — sem semântica nenhuma, ele só devolve 1.0 para textos idênticos. É o motivo de `backend: mock` servir apenas para CI.

## Passo 3 — Mini-busca: o ranking inverte (8 min)

Agora o cenário real de RAG: uma pergunta contra 6 "documentos" de banco.

🎲 **APOSTA:** a pergunta é *"Pago menos juros se já for cliente antigo do banco?"*. A resposta certa é o documento sobre desconto por relacionamento. **A busca léxica vai colocá-lo em 1º lugar?**

```bash
python scripts/lab_lexico_vs_semantico.py --busca
```

<details>
<summary>Gabarito do Passo 3</summary>

- **Léxico:** o documento certo ("Clientes com relacionamento acima de 5 anos têm desconto na taxa...") ficou em **4º lugar** com score 0.04 — a pergunta usa "juros", "antigo", "pago"; o documento usa "desconto", "relacionamento", "taxa". Quase nenhuma palavra bate. O 1º lugar léxico é um documento errado (empate técnico em 0.05).
- **Semântico:** o documento certo ficou em **1º lugar** com folga (0.57 contra 0.43 do segundo).

Reparem também nos **valores absolutos** do ranking semântico: o certo tem 0.57 e o irrelevante (PIX) tem 0.09. É esse intervalo que o `min_similarity_score: 0.35` do `config/memory_policy.yaml` corta — abaixo disso, o chunk nem entra no prompt do agente.

</details>

Testem com uma pergunta do grupo (vale tentar quebrar a busca semântica!):

```bash
python scripts/lab_lexico_vs_semantico.py --busca --query "escreva a pergunta do grupo"
```

## Passo 4 — Caça à armadilha (7 min)

Desafio entre grupos: usando pares customizados, encontrem **um par onde o juiz semântico se engana** — ou dá score alto para sentidos diferentes (como o P2), ou score baixo para o mesmo sentido.

```bash
python scripts/lab_lexico_vs_semantico.py --par "frase A do grupo" "frase B do grupo"
```

Ideias de ataque: inversão de papéis ("A deve para B" / "B deve para A"), negação ("aprovado" / "não aprovado"), números ("taxa de 1%" / "taxa de 9%"), ironia.

**Cada grupo apresenta sua melhor armadilha em 30 segundos.** Vence a que tiver o score mais "errado".

## Discussão de fechamento (5 min)

1. **Quando o léxico ainda vence?** Códigos exatos, nomes próprios, números de contrato, siglas — casos onde "parecido" não serve, só "igual". Por isso sistemas reais usam **hybrid search** (léxico + semântico combinados) — tema do material `hybrid_search.html`.
2. **O que a armadilha do P2 implica para o nosso agente?** O RAG pode recuperar um chunk com os papéis invertidos e o LLM confiar nele. Mitigações: chunks com contexto suficiente, reranking, metadados.
3. **Conexão com o pipeline:** tudo que vocês mediram aqui é o que acontece dentro de `LongTermMemoryGateway.search_customer_insights()` — embedding da query, cosseno contra o ChromaDB, corte por `min_similarity_score`.

## Critério de conclusão

- [ ] Fizeram as 12 apostas antes da revelação e contaram o placar
- [ ] Sabem explicar P1 (por que léxico falha) e P2 (por que semântico também falha)
- [ ] Viram a inversão de ranking na mini-busca (4º léxico → 1º semântico)
- [ ] Encontraram (ou tentaram) uma armadilha própria no Passo 4
- [ ] Sabem dizer onde o `min_similarity_score` entra nessa história

## Troubleshooting

| Problema | Ação |
|----------|------|
| `ImportError: sentence_transformers` | `pip install -e ".[lab]"` na raiz do repo |
| Acentos quebrados no terminal | Use Windows Terminal ou Git Bash; o script já força UTF-8 |
| Scores um pouco diferentes do gabarito | Versão do modelo/lib; os *contrastes* (alto × baixo) devem se manter |
| `--par` com erro de argumentos | Coloque cada frase entre aspas: `--par "frase A" "frase B"` |

## Próximo

Com dimensões e similaridade dominadas, o próximo passo é o vector store em escala: [Tutorial Vertex AI Vector Search](02-tutorial-vertex-vector-search.md) — e, no agente, o RAG condicional da [Aula 3](../aula-03-agente-stateful/01-teoria-agente-the-memory.md).
