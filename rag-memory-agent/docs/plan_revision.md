# Revisão do plano RAG (Architecture + State em blocos)

Documento de revisão crítica do plano executado (Blocos 0–3). Objetivo: identificar o que o plano cobriu bem, o que faltou e o que melhorar em planos futuros ou em uma próxima iteração.

---

## 1. O que o plano acertou

- **Escopo bem definido**: 7 problemas mapeados com arquivo e ação; blocos 0–3 com entregas claras.
- **Separação de responsabilidades**: Bloco 1 (embedding + gateway), Bloco 2 (router + testes), Bloco 3 (validação/docs) evita misturar muitas mudanças em um único passo.
- **Regra de contexto**: “Carregar apenas state_rag.md e architecture.md entre blocos” reduz risco de alucinação e mantém rastreabilidade.
- **Referências de código**: Linhas e arquivos citados (embedding.py, memory_gateway, agent_router) permitem executar sem redescobrir tudo.
- **Artefatos úteis**: architecture.md e state_rag.md reestruturado servem como documentação e onboarding.

---

## 2. Lacunas do plano (o que faltou especificar)

### 2.1 Backend Vertex

- O plano tratou apenas **Chroma** para min_similarity, distances e where.
- No código, o branch **Vertex** (`search_memory`) não usa `where_metadata`, não aplica `min_similarity_score` e não ordena por score (depende do que o serviço retorna).
- **Melhoria**: No plano, incluir item explícito: “Vertex: aplicar filtro por score e where quando a API do Vertex permitir; ou documentar que Vertex segue comportamento padrão do serviço”.

### 2.2 Backend mock

- O **mock** ignora `where_metadata` e não simula score; retorna texto fixo por substring na query.
- **Melhoria**: No plano ou na architecture, documentar que “mock não aplica where_metadata nem min_similarity; usado apenas para testes de integração e degradação”.

### 2.3 Comportamento quando `where` retorna vazio

- Se todos os chunks forem de outras sessões (ou não tiverem `session_id`), o Chroma com `where={"session_id": session_id}` pode devolver 0 resultados.
- Hoje o agente recebe string vazia e segue sem RAG. O plano não definiu se deve haver **fallback** (ex.: nova busca sem where) ou se “vazio” é o comportamento desejado.
- **Melhoria**: Incluir no plano uma “decisão de produto”: “Quando where retorna 0 resultados: (A) retornar vazio; (B) tentar busca sem where com limite menor”. Documentar a escolha na architecture.

### 2.4 Teste E2E

- O plano deixou E2E como “opcional” sem critérios de aceite.
- **Melhoria**: Definir um E2E mínimo, por exemplo: “Indexar data/sample_insights.csv com --push (Chroma temporário); chamar search_customer_insights com query que contenha session_id do CSV; assert que o texto do insight correspondente aparece no resultado”.

### 2.5 Critérios de sucesso por bloco

- O plano não exigiu explicitamente “pytest verde” ou “nenhuma regressão” ao fim de cada bloco (só no Bloco 3).
- **Melhoria**: Para cada Bloco 1 e 2, acrescentar: “Critério de conclusão: pytest deve passar; testes existentes não podem quebrar”.

### 2.6 Fórmula de similaridade

- O plano disse “similaridade = 1 - distance” para cosine, mas não mencionou que o Chroma pode retornar distâncias em escalas diferentes nem o uso de `max(0, 1 - distance)` para evitar valor negativo.
- **Melhoria**: Na seção “Referências de código” ou na architecture, documentar: “Chroma cosine: similarity = max(0, 1 - distance); threshold min_similarity_score aplicado após conversão”.

### 2.7 Dimensão do mock vs Vertex

- O embedding mock produz vetores de 768 dimensões (igual ao Vertex text-multilingual-embedding-002) para compatibilidade ao alternar entre mock e Vertex.
- **Melhoria**: Incluir no plano ou na architecture: “Em ambiente com Vertex para indexação e mock para testes, as dimensões devem ser compatíveis; mock pode ser configurado para 768 ou testes devem usar apenas mock end-to-end”.

---

## 3. Melhorias sugeridas para uma próxima versão do plano

1. **Incluir “Critérios de conclusão” por bloco**: pytest verde, sem regressão, lista de arquivos alterados.
2. **Tratar os três backends**: Chroma (detalhado), Vertex (aplicar score/where ou documentar limitações), Mock (documentar que where/score não se aplicam).
3. **Definir decisão quando where retorna vazio**: comportamento atual (vazio) ou fallback; registrar na architecture.
4. **E2E com aceite claro**: um cenário mínimo (indexar sample → buscar → assert conteúdo) com passos e assertivas.
5. **Documentar fórmula de score**: similarity = max(0, 1 - distance) e onde se aplica (Chroma).
6. **Opcional – Bloco 4 ou “Fase 2”**: Vertex upsert real, re-ranking, pipeline RAG configurável, com mesmo padrão de state + architecture entre blocos.
7. **Correção na architecture**: typo “Origen” → “Origem” na seção 4 (Fluxo RAG — Consulta).

---

## 4. Resumo

| Aspecto | Avaliação | Ação sugerida |
|--------|-----------|----------------|
| Escopo dos 7 problemas | Bom | Manter |
| Blocos 0–3 | Bom | Adicionar critérios de conclusão por bloco |
| Chroma (min_similarity, where, ordenação) | Coberto | Manter |
| Vertex | Parcial | Documentar ou alinhar score/where |
| Mock | Parcial | Documentar que where/score não se aplicam |
| Comportamento where vazio | Não especificado | Decidir e documentar |
| E2E | Opcional sem critério | Definir E2E mínimo com aceite |
| Fórmula de similaridade | Implícita | Documentar na architecture |
| Dimensão mock vs Vertex | Não tratada | Documentar ou alinhar em testes |

Com essas melhorias, uma próxima iteração do plano (ou um “Plano v2” para re-ranking, Vertex e E2E) fica mais completa e reproduzível.

---

## 5. Implementação das melhorias

As melhorias acima foram implementadas em blocos (ver [state_rag.md](../state_rag.md), seção "Melhorias pós-revisão do plano"):

- **Bloco A:** Documentação em docs/architecture.md (fórmula de similaridade, decisão when where vazio, tabela Chroma/Vertex/Mock, dimensão mock vs Vertex); critérios de conclusão nos Blocos 1–3 do state_rag; docstrings em memory_gateway (comportamento por backend e when where vazio).
- **Bloco B:** Teste E2E `test_rag_e2e_index_search_with_where` (indexar CSV com session_id, upsert Chroma, buscar com query e where_metadata, assert conteúdo do insight).
- **Bloco C:** state_rag atualizado com seção "Melhorias pós-revisão"; plan_revision com esta seção.
