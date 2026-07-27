# Tutorial de Aula (40 minutos): Governance Gateway

> **Público:** alunos que já sabem Python básico, mas nunca construíram um sistema com LLM.
> **Objetivo da aula:** ao final, o aluno entende **por que** e **como** um sistema decide qual modelo LLM usar, quanto isso custa, e como organizar um projeto de agente de IA de forma auditável.
> **Formato:** aula expositiva + demonstração ao vivo. Nenhuma credencial GCP é necessária (tudo roda em modo simulação).

---

## Mapa da Aula (visão do professor)

| Bloco | Tempo     | Tema                                             | Recurso                       |
| ----- | --------- | ------------------------------------------------ | ----------------------------- |
| 0     | 0–5 min   | O problema: "scripts soltos e a conta invisível" | Slide/quadro (storytelling)   |
| 1     | 5–12 min  | Tour pelo projeto: a estrutura ADK               | VS Code aberto no repositório |
| 2     | 12–20 min | O Router: quem decide o modelo?                  | `src/router.py` + YAML        |
| 3     | 20–28 min | FinOps: quanto custa cada pergunta?              | `src/telemetry.py`            |
| 4     | 28–34 min | Prompt, validação e o "LLM falso"                | `prompts/` + `src/models.py`  |
| 5     | 34–40 min | Demo final + gancho para o Lab                   | `python main.py`              |

**Preparação antes da aula (5 min):**

```bash
cd agente-1-the-governance-gateway
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py                 # confirme que roda sem erros
```

> Dica Windows: se aparecer `UnicodeEncodeError`, rode `chcp 65001` antes, ou defina `PYTHONIOENCODING=utf-8`.

---

## BLOCO 0 (0–5 min) — O Problema: a conta invisível

**Não abra código ainda.** Comece com uma história:

> "Imaginem um banco. O time jurídico criou um script Python que usa o Gemini para revisar contratos. O RH copiou o script para responder dúvidas de férias. A TI copiou para analisar logs. Seis meses depois, chega uma fatura de **US$ 40.000/mês** do Google Cloud. Ninguém sabe qual time gastou o quê, nem por quê."

Escreva no quadro os **dois problemas** que este projeto resolve:

1. **Desperdício invisível** — todo mundo usa o modelo mais caro (Pro) para tudo, inclusive para perguntas triviais que um modelo 16x mais barato (Flash) responderia igual.
2. **Caos de governança** — cada script tem seu prompt hardcoded, sua configuração hardcoded. Impossível auditar, impossível mudar sem redeployar.

**Pergunta provocativa para a turma:**

> "Se o Gemini Pro custa ~16x mais que o Flash, e 70% das perguntas são simples... quanto dinheiro estamos jogando fora?"

Deixe-os fazer a conta mental. A resposta aparece no Bloco 3.

**A solução tem nome:** padrão **Router-Gateway**.

- **Router** = o "porteiro" que olha quem está pedindo e o quão difícil é o pedido, e escolhe o modelo adequado.
- **Gateway** = o "balcão único" por onde todas as chamadas ao LLM passam (será construído no Lab).

---

## BLOCO 1 (5–12 min) — Tour pelo Projeto: a estrutura ADK

Abra o VS Code no projeto e mostre a árvore de pastas. **Não entre nos arquivos ainda** — o objetivo aqui é a arquitetura, não o código.

```
agente-1-the-governance-gateway/
├── main.py                  ← Ponto de entrada (python main.py)
├── config/                  ← REGRAS DE NEGÓCIO (YAML, sem código)
│   ├── model_policy.yaml    ← Quem usa qual modelo + preços
│   └── safety_settings.yaml ← Filtros de segurança do modelo
├── prompts/                 ← PROMPTS VERSIONADOS (fora do código)
│   ├── audit_master.jinja2  ← O "roteiro" que o LLM recebe
│   └── user_intent.yaml     ← Exemplos few-shot (aula futura)
├── src/                     ← CÓDIGO PYTHON
│   ├── router.py            ← Decide o modelo (Router)
│   ├── telemetry.py         ← Calcula custo (FinOps)
│   ├── models.py            ← Valida dados (Pydantic)
│   ├── main.py              ← Orquestra a demonstração
│   ├── logger.py            ← Logs estruturados
│   └── exceptions.py        ← Erros com nome próprio
└── tests/                   ← 44 testes automatizados
```

**Conceito-chave a fixar: ADK (Agent Development Kit) — separação de responsabilidades.**

Use esta analogia:

> "Pensem num restaurante. O **cardápio** (`config/`) diz o que servir e por quanto. A **receita** (`prompts/`) diz como preparar. A **cozinha** (`src/`) executa. Se o dono quer mudar o preço do prato, ele **não reforma a cozinha** — ele reimprime o cardápio."

Por que isso importa (escreva os 3 pontos):

1. **Versionamento:** mudou o prompt? O Git mostra quem, quando e o quê. Num banco, isso é requisito de auditoria.
2. **Mudança sem deploy:** o time de FinOps altera um YAML e pronto — nenhum programador envolvido, nenhum redeploy.
3. **Revisão:** um pull request que muda `complexity_threshold: 0.5 → 0.7` é legível até para quem não programa.

**Momento de checagem (pergunte à turma):**

> "Se eu quiser que o RH passe a usar sempre o modelo barato, qual arquivo eu mudo?" (Resposta esperada: `config/model_policy.yaml` — nenhum `.py`.)

---

## BLOCO 2 (12–20 min) — O Router: quem decide o modelo?

Agora sim, abra `config/model_policy.yaml`. Este é o coração conceitual do projeto:

```yaml
departments:
  legal_dept: # Jurídico
    tier: platinum # SEMPRE o modelo caro
    model: gemini-2.5-pro
    complexity_threshold: null

  hr_dept: # RH
    tier: standard # DEPENDE da complexidade
    model: null
    complexity_threshold: 0.5 # < 0.5 → Flash | >= 0.5 → Pro

  it_ops: # TI
    tier: budget # SEMPRE o modelo barato
    model: gemini-2.5-flash
    complexity_threshold: null
```

Desenhe a **árvore de decisão** no quadro:

```
                 requisição chega
                 (departamento + complexidade 0.0–1.0)
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
        platinum     standard     budget
            │           │           │
            ▼           ▼           ▼
        sempre     complexidade   sempre
          PRO       < 0.5? ──sim──► FLASH
                        │
                        não
                        ▼
                       PRO
```

**Explique os tiers com casos reais:**

- **platinum (Jurídico):** um erro numa cláusula de contrato custa milhões. O custo do modelo é irrelevante perto do risco. → sempre Pro.
- **budget (TI Ops):** "consultar logs" é trivial. Pagar 16x mais por isso é desperdício puro. → sempre Flash.
- **standard (RH):** aqui mora a inteligência. "Ver saldo de férias" (complexidade 0.3) → Flash. "Analisar processo trabalhista" (complexidade 0.8) → Pro.

Agora abra `src/router.py` e mostre **apenas** o método `route_request()` (linhas ~142–250). Pontos a destacar:

1. O router **não tem regra de negócio hardcoded** — ele lê o tier do YAML e aplica.
2. Validações de fronteira: departamento inexistente → `DepartmentNotFoundError`; complexidade fora de 0.0–1.0 → `InvalidComplexityError`. **Falhar cedo e com erro nomeado** é o que separa código profissional de script solto.
3. O router é _stateless_: toda a política vem do YAML na inicialização.

**Exercício relâmpago (2 min):** peça a um aluno para prever, sem rodar:

> "hr_dept, complexidade 0.5 — Flash ou Pro?"
> (Pegadinha: a regra é `< 0.5` usa Flash, então **0.5 exato vai para Pro**. Está na linha `if complexity_score < threshold`.)

---

## BLOCO 3 (20–28 min) — FinOps: quanto custa cada pergunta?

**Retome a pergunta do Bloco 0.** Agora com números. Escreva no quadro:

| Modelo           | Input (1M tokens) | Output (1M tokens) |
| ---------------- | ----------------- | ------------------ |
| **Gemini Flash** | $0.075            | $0.30              |
| **Gemini Pro**   | $1.25             | $5.00              |

**Conta ao vivo** (requisição típica: 1.000 tokens input, 500 output):

- Flash: `1.0 × $0.075 + 0.5 × $0.30` = **$0.225** _(por mil requisições)_
- Pro: `1.0 × $1.25 + 0.5 × $5.00` = **$3.75** _(por mil requisições)_
- **Pro é ~16,7x mais caro.**

Projeção anual com 1.000 requisições/dia:

- Sempre Pro: ~**$1.368/ano** por agente
- Roteamento inteligente (70% Flash / 30% Pro): ~**$292/ano** por agente
- **Economia: 79%.** Em 50 agentes: **~$53.800/ano** — sem escrever uma linha de código a mais, só política.

**Agora o conceito técnico: o que é um token?**

> "O modelo não cobra por caractere nem por palavra. Cobra por **token** — pedaços de texto de tamanho variável. 'Preciso revisar o contrato' (30 caracteres) ≈ 8 tokens. Em média, 1 token ≈ 4 caracteres, mas isso varia ±30% conforme o idioma."

Abra `src/telemetry.py` e mostre dois pontos:

1. **`_count_tokens()`** — usa a biblioteca `tiktoken` para contagem precisa. Se ela não estiver instalada, cai no fallback `caracteres ÷ 4`. Pergunte: "por que ±30% de erro na contagem é inaceitável em FinOps?" (Porque o erro se propaga direto para a fatura estimada.)
2. **`calculate_cost()`** — a fórmula:

```python
custo = (input_tokens / 1000) * preço_input_por_1k \
      + (output_tokens / 1000) * preço_output_por_1k
```

**Detalhe honesto para contar à turma:** os preços vêm do mesmo `model_policy.yaml` (seção `pricing`). Ou seja, o time de FinOps atualiza preço no YAML quando o Google muda a tabela — de novo, sem tocar em código. E em produção nem precisaremos estimar: a API do Google devolve a contagem exata de tokens em cada resposta (`usage_metadata`) — isso vem no Lab.

---

## BLOCO 4 (28–34 min) — Prompt, validação e o "LLM falso"

Três peças rápidas, uma por minuto de código na tela:

### 4.1 O prompt como artefato versionado (`prompts/audit_master.jinja2`)

Mostre o template. Destaque:

- O prompt define uma **persona** ("Você é um Auditor de Governança do Banco Votorantim").
- Exige **saída JSON com formato obrigatório** — isso é o que torna a resposta do LLM consumível por código.
- `{{ user_request }}` é uma variável Jinja2: o mesmo template serve para qualquer pergunta.

> "Prompt não é string dentro do código. Prompt é **artefato de engenharia**: versionado, revisado, testado."

### 4.2 O contrato de dados (`src/models.py`)

Mostre `AuditResponse`:

```python
class AuditResponse(BaseModel):
    compliance_status: Literal["APPROVED", "REJECTED", "REQUIRES_REVIEW"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    audit_reasoning: str  # mínimo 10 caracteres
```

> "LLMs mentem, inventam e mudam de formato. O Pydantic é o segurança na porta: se o JSON vier fora do contrato, **explode aqui**, não três camadas depois num sistema bancário."

### 4.3 O LLM falso (`src/main.py`, função `simulate_llm_response()`)

**Momento de transparência — este é o ponto mais importante da aula:**

> "Este projeto **não chama nenhuma IA de verdade**. A função `simulate_llm_response()` é um `if/elif` de palavras-chave: se o pedido contém 'excluir' → REJECTED; 'transferência' → REQUIRES_REVIEW; 'consulta' → APPROVED."

Pergunte: **"Por que fizemos isso de propósito?"**

1. Foco: a aula é sobre **arquitetura e custos**, não sobre a API do Google.
2. Zero custo e zero credencial para 40 alunos rodarem em casa.
3. Testabilidade: os 44 testes rodam em qualquer máquina, sem rede.

> "E é exatamente esta função que vocês vão **substituir por uma chamada real** no Lab Guiado."

---

## BLOCO 5 (34–40 min) — Demo Final ao Vivo

Rode no terminal, com a turma acompanhando:

```bash
python main.py
```

Narre os 3 cenários conforme aparecem na tela:

| Cenário | Departamento | Complexidade | Modelo esperado | Por quê                    |
| ------- | ------------ | ------------ | --------------- | -------------------------- |
| 1       | Jurídico     | 0.8          | **Pro**         | tier platinum → sempre Pro |
| 2       | RH           | 0.3          | **Flash**       | 0.3 < 0.5 (threshold)      |
| 3       | TI Ops       | 0.2          | **Flash**       | tier budget → sempre Flash |

Para cada cenário, aponte na tabela do terminal: modelo escolhido, **custo estimado** (repare que o cenário 1, com Pro, custa uma ordem de grandeza mais que os outros) e o JSON do "auditor".

**Experimento ao vivo (se der tempo — 2 min):**
Abra `config/model_policy.yaml`, mude o threshold do RH de `0.5` para `0.2`, rode de novo. O cenário 2 agora usa **Pro** (0.3 >= 0.2). Frase de efeito:

> "Acabei de mudar o comportamento de um sistema de IA em produção **sem tocar em uma linha de Python**. Isso é o Router-Gateway."

_(Desfaça a mudança depois.)_

### Fechamento (1 min)

Recapitule os 4 conceitos no quadro:

1. **ADK** — config, prompts e código separados → auditável.
2. **Router-Gateway** — a escolha do modelo é política, não código.
3. **FinOps** — token é dinheiro; medir é o primeiro passo para economizar (79%!).
4. **Contrato de dados** — Pydantic protege o sistema do que o LLM devolve.

**Gancho:**

> "Hoje o LLM é falso. Na próxima etapa — o Lab Guiado — vocês vão conectar este gateway ao **Gemini de verdade** na Google Cloud, com autenticação, tokens reais e custo real. Documento: `doc/lab-guiado-vertex-ai.md`."

---

## Apêndice para o Professor

### Perguntas frequentes dos alunos (e respostas curtas)

- **"tiktoken é da OpenAI, funciona pra Gemini?"** — É uma aproximação (~95%). Em produção a API devolve a contagem exata; o tiktoken serve para estimar **antes** de chamar.
- **"Por que YAML e não banco de dados?"** — YAML entra no Git → todo change vira commit revisável. Para políticas que mudam pouco, é a forma mais auditável.
- **"E se dois departamentos precisarem de regras diferentes de segurança?"** — Ótima pergunta; é o tema das próximas aulas (Intent Guardrail por política).
- **"Esse nome `gemini-2.5-pro` ainda existe?"** — Não! Os modelos 1.5 foram aposentados pelo Google em 2025. Como aqui é simulação, o nome é só uma string. No Lab, atualizamos para `gemini-2.5-*`.

### Comandos de apoio

```bash
pytest tests/ -v            # mostrar os 44 testes passando (bom para abrir o Bloco 4)
pytest tests/test_router.py -v   # só o router
```

### O que NÃO cabe em 40 minutos (não tente)

- Ler `logger.py` e `exceptions.py` linha a linha — apenas cite que existem.
- Explicar Jinja2 a fundo — mostre só o `{{ user_request }}`.
- Discutir preços atuais do Google — os do YAML são didáticos; os reais ficam para o Lab.
