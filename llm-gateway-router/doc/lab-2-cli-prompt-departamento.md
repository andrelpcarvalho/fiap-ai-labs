# Lab 2: CLI com Prompt e Departamento

> **Objetivo:** permitir que o usuário informe o **departamento** e o **prompt** pela linha de comando, em vez de depender só dos 3 cenários fixos no código. A demo sem argumentos continua funcionando.
>
> **Duração estimada:** 30–40 minutos.
>
> **Pré-requisito:** `python main.py` já roda (Lab 1 / Vertex AI é opcional). Este lab funciona com `USE_MOCK=true`.

---

## Como este Lab está organizado

| Parte | Quem executa | O quê                                          |
| ----- | ------------ | ---------------------------------------------- |
| 0     | Aluno        | Entender o problema e o comportamento desejado |
| 1     | Aluno        | Extrair constantes e o mapa de nomes/defaults  |
| 2     | Aluno        | Implementar `parse_args()`                     |
| 3     | Aluno        | Implementar `build_scenarios()`                |
| 4     | Aluno        | Ligar tudo no `main()`                         |
| 5     | Aluno        | Escrever testes                                |
| 6     | Aluno        | Rodar, validar e experimentar tiers            |

---

## PARTE 0 — O problema

Hoje, em `src/main.py`, a lista `scenarios` está **hardcoded** dentro de `main()`:

```python
scenarios = [
    {"department": "legal_dept", "user_request": "...", "complexity": 0.8},
    {"department": "hr_dept",    "user_request": "...", "complexity": 0.3},
    {"department": "it_ops",     "user_request": "...", "complexity": 0.2},
]
```

Para testar outro prompt ou outro departamento, o aluno teria que editar o código. No Lab 2, a entrada vira CLI:

```text
python main.py
  → 3 cenários demo (comportamento atual)

python main.py --dept hr_dept --prompt "Verificar saldo de férias"
  → 1 requisição customizada

python main.py --dept hr_dept
  → ERRO (faltou --prompt)

python main.py --prompt "Algo"
  → ERRO (faltou --dept)
```

Departamentos válidos (já definidos em `config/model_policy.yaml`):

| ID           | Nome amigável         | Tier     |
| ------------ | --------------------- | -------- |
| `legal_dept` | Departamento Jurídico | platinum |
| `hr_dept`    | Recursos Humanos      | standard |
| `it_ops`     | Operações de TI       | budget   |

> **Importante:** o `argparse` já está importado em `src/main.py`, mas ainda não é usado. Você vai usá-lo agora.

---

## PARTE 1 — Constantes (antes de `main`)

Abra `src/main.py`. **Antes** da função `main()`, adicione três constantes. A lista de cenários demo sai de dentro do `main` e vira constante reutilizável.

### 1.1 Colar isto acima de `def main():`

```python
DEPARTMENT_NAMES = {
    "legal_dept": "Departamento Jurídico",
    "hr_dept": "Recursos Humanos",
    "it_ops": "Operações de TI",
}

DEFAULT_COMPLEXITY = {
    "legal_dept": 0.8,
    "hr_dept": 0.3,
    "it_ops": 0.2,
}

DEMO_SCENARIOS = [
    {
        "department": "legal_dept",
        "department_name": "Departamento Jurídico",
        "user_request": (
            "Preciso revisar o contrato de parceria com a empresa XYZ "
            "para verificar cláusulas de confidencialidade"
        ),
        "complexity": 0.8,
    },
    {
        "department": "hr_dept",
        "department_name": "Recursos Humanos",
        "user_request": "Verificar saldo de férias do funcionário ID 12345",
        "complexity": 0.3,
    },
    {
        "department": "it_ops",
        "department_name": "Operações de TI",
        "user_request": "Consultar logs de acesso do sistema de gestão",
        "complexity": 0.2,
    },
]
```

> **Discussão em sala:** por que defaults de complexidade por departamento? Porque o tier `standard` (`hr_dept`) usa o `complexity_score` para escolher Flash vs Pro. Sem um default, a CLI ficaria incompleta.

### 1.2 Remover a lista antiga

Dentro de `main()`, **apague** o bloco `scenarios = [ ... ]` antigo. Na Parte 4 você vai substituí-lo por `build_scenarios(...)`.

---

## PARTE 2 — Implementar `parse_args()`

Ainda em `src/main.py`, **abaixo das constantes** e **acima de `main()`**, crie:

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Interpreta argumentos de linha de comando.

    Sem --dept/--prompt: modo demo (3 cenários fixos).
    Com ambos: processa uma única requisição customizada.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Governance Gateway — roteamento de modelos LLM. "
            "Sem argumentos, executa a demo com 3 cenários. "
            "Com --dept e --prompt, processa uma requisição customizada."
        )
    )
    parser.add_argument(
        "--dept",
        dest="department",
        help="ID do departamento (ex: legal_dept, hr_dept, it_ops)",
    )
    parser.add_argument(
        "--prompt",
        dest="user_request",
        help="Solicitação do usuário a ser auditada",
    )
    parser.add_argument(
        "--complexity",
        type=float,
        default=None,
        help="Complexidade da requisição (0.0–1.0). Default depende do departamento.",
    )
    args = parser.parse_args(argv)

    has_dept = args.department is not None
    has_prompt = args.user_request is not None
    if has_dept != has_prompt:
        parser.error(
            "Use --dept e --prompt juntos. "
            "Exemplo: python main.py --dept hr_dept --prompt \"Sua solicitação\""
        )

    if args.complexity is not None and not (0.0 <= args.complexity <= 1.0):
        parser.error("--complexity deve estar entre 0.0 e 1.0")

    return args
```

**Pontos para discutir:**

1. `dest="department"` — o flag na CLI é `--dept`, mas no código o atributo fica `args.department` (nome alinhado ao restante do projeto).
2. `parser.error(...)` — gera `SystemExit` com mensagem clara (exit code != 0). Ideal para lab e para scripts.
3. `argv=None` — permite testes unitários sem mexer em `sys.argv`: `parse_args(["--dept", "hr_dept", "--prompt", "x"])`.

### 2.1 Teste rápido (ainda sem ligar no `main`)

No Python interativo ou num scratch:

```python
from src.main import parse_args
parse_args([])  # ok
parse_args(["--dept", "hr_dept"])  # deve falhar
```

---

## PARTE 3 — Implementar `build_scenarios()`

Logo abaixo de `parse_args()`, adicione:

```python
def build_scenarios(args: argparse.Namespace, router: ModelRouter) -> list[dict]:
    """
    Monta a lista de cenários a processar.

    - Sem --dept/--prompt: retorna os 3 cenários demo.
    - Com ambos: valida o departamento e retorna um único cenário.
    """
    if args.department is None and args.user_request is None:
        return [scenario.copy() for scenario in DEMO_SCENARIOS]

    valid_depts = list(router.departments.keys())
    if args.department not in router.departments:
        raise ValueError(
            f"Departamento '{args.department}' inválido. "
            f"Válidos: {valid_depts}"
        )

    complexity = args.complexity
    if complexity is None:
        complexity = DEFAULT_COMPLEXITY.get(args.department, 0.5)

    return [
        {
            "department": args.department,
            "department_name": DEPARTMENT_NAMES.get(
                args.department, args.department
            ),
            "user_request": args.user_request,
            "complexity": complexity,
        }
    ]
```

**Pontos para discutir:**

1. Validar contra `router.departments` (vindo do YAML) — se o professor adicionar um departamento novo na política, a CLI aceita sem mudar o validador hardcoded (só o nome amigável cairia no fallback `args.department`).
2. `.copy()` nos demos — evita mutação acidental da constante `DEMO_SCENARIOS`.
3. O loop que processa cenários (Router → mock/Gemini → custo) **não muda**. Só a origem da lista muda.

---

## PARTE 4 — Ligar no `main()`

### 4.1 Assinatura e parse no início

Troque:

```python
def main():
```

por:

```python
def main(argv: list[str] | None = None):
```

No **começo** de `main()`, antes do `setup_logging`:

```python
    args = parse_args(argv)
```

### 4.2 Substituir a lista fixa

Onde estava o `scenarios = [ ... ]` antigo (que você removeu na Parte 1), coloque:

```python
    # ------------------------------------------------------------------------
    # Cenários (demo ou customizado via CLI)
    # ------------------------------------------------------------------------
    try:
        scenarios = build_scenarios(args, router)
    except ValueError as e:
        logger.error(str(e))
        console.print(f"[bold red]{e}[/bold red]")
        return
```

> `router` já foi criado algumas linhas acima — use o mesmo objeto. A validação de departamento precisa da política carregada.

### 4.3 O resto do `main()`

**Não altere** o `for idx, scenario in enumerate(scenarios, 1):` nem o fluxo mock/real. Se o Lab 1 (Vertex) estiver feito, `--dept`/`--prompt` já funcionam em modo real também.

### 4.4 Entrada na raiz

O arquivo `main.py` na raiz já faz:

```python
from src.main import main

if __name__ == "__main__":
    main()
```

Isso basta: `argparse` lê `sys.argv` quando `argv=None`. Não precisa mudar a raiz.

### 4.5 Validar a implementação

```bash
python main.py --help
python main.py
python main.py --dept hr_dept --prompt "Verificar saldo de férias do ID 12345"
python main.py --dept hr_dept
```

Esperado:

| Comando               | Resultado                                              |
| --------------------- | ------------------------------------------------------ |
| `--help`              | lista `--dept`, `--prompt`, `--complexity`             |
| sem args              | 3 cenários                                             |
| `--dept` + `--prompt` | 1 cenário (RH → `gemini-2.5-flash` com complexity 0.3) |
| só `--dept`           | erro pedindo os dois flags juntos                      |

---

## PARTE 5 — Testes

Abra `tests/test_main.py`. Importe as novas funções e o router:

```python
from src.main import (
    render_prompt_template,
    simulate_llm_response,
    simulate_input_output,
    parse_args,
    build_scenarios,
)
from src.router import ModelRouter
```

### 5.1 Classe `TestParseArgs`

Adicione no final do arquivo:

```python
class TestParseArgs:
    """Testes para parse_args (Lab 2 — CLI)."""

    def test_parse_args_no_args(self):
        args = parse_args([])
        assert args.department is None
        assert args.user_request is None
        assert args.complexity is None

    def test_parse_args_dept_and_prompt(self):
        args = parse_args([
            "--dept", "hr_dept",
            "--prompt", "Verificar saldo de férias",
        ])
        assert args.department == "hr_dept"
        assert args.user_request == "Verificar saldo de férias"
        assert args.complexity is None

    def test_parse_args_with_complexity(self):
        args = parse_args([
            "--dept", "legal_dept",
            "--prompt", "Revisar NDA",
            "--complexity", "0.9",
        ])
        assert args.complexity == 0.9

    def test_parse_args_only_dept_raises(self):
        with pytest.raises(SystemExit):
            parse_args(["--dept", "hr_dept"])

    def test_parse_args_only_prompt_raises(self):
        with pytest.raises(SystemExit):
            parse_args(["--prompt", "Algo"])

    def test_parse_args_invalid_complexity_raises(self):
        with pytest.raises(SystemExit):
            parse_args([
                "--dept", "hr_dept",
                "--prompt", "Teste",
                "--complexity", "1.5",
            ])
```

### 5.2 Classe `TestBuildScenarios`

```python
class TestBuildScenarios:
    """Testes para build_scenarios (Lab 2 — CLI)."""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_build_scenarios_demo(self, router):
        args = parse_args([])
        scenarios = build_scenarios(args, router)
        assert len(scenarios) == 3
        assert scenarios[0]["department"] == "legal_dept"
        assert scenarios[1]["department"] == "hr_dept"
        assert scenarios[2]["department"] == "it_ops"

    def test_build_scenarios_custom(self, router):
        args = parse_args([
            "--dept", "it_ops",
            "--prompt", "Consultar logs do sistema",
        ])
        scenarios = build_scenarios(args, router)
        assert len(scenarios) == 1
        assert scenarios[0]["department"] == "it_ops"
        assert scenarios[0]["user_request"] == "Consultar logs do sistema"
        assert scenarios[0]["department_name"] == "Operações de TI"
        assert scenarios[0]["complexity"] == 0.2

    def test_build_scenarios_default_complexity_by_dept(self, router):
        for dept, expected in [
            ("legal_dept", 0.8),
            ("hr_dept", 0.3),
            ("it_ops", 0.2),
        ]:
            args = parse_args(["--dept", dept, "--prompt", "teste"])
            scenarios = build_scenarios(args, router)
            assert scenarios[0]["complexity"] == expected

    def test_build_scenarios_custom_complexity(self, router):
        args = parse_args([
            "--dept", "hr_dept",
            "--prompt", "Análise complexa de folha",
            "--complexity", "0.7",
        ])
        scenarios = build_scenarios(args, router)
        assert scenarios[0]["complexity"] == 0.7

    def test_build_scenarios_invalid_department(self, router):
        args = parse_args([
            "--dept", "marketing_dept",
            "--prompt", "Campanha",
        ])
        with pytest.raises(ValueError) as exc_info:
            build_scenarios(args, router)
        assert "inválido" in str(exc_info.value)
```

### 5.3 Rodar os testes

```bash
pytest tests/test_main.py -v -k "ParseArgs or BuildScenarios"
pytest tests/ -v
```

Tudo deve passar.

---

## PARTE 6 — Experimentar (FinOps na prática)

Com a CLI pronta, compare o **modelo escolhido** (e o custo) nestes comandos. Preferível com `USE_MOCK=true` primeiro (zero custo):

```bash
# Platinum → sempre Pro
python main.py --dept legal_dept --prompt "Revisar NDA com fornecedor"

# Standard + baixa complexidade → Flash
python main.py --dept hr_dept --prompt "Consultar saldo de férias" --complexity 0.2

# Standard + alta complexidade → Pro
python main.py --dept hr_dept --prompt "Analisar política de benefícios completa" --complexity 0.8

# Budget → sempre Flash
python main.py --dept it_ops --prompt "Consultar logs de acesso"
```

Se o Lab 1 estiver concluído, troque para `USE_MOCK=false` e rode **um** comando customizado — o `audit_reasoning` passa a ser texto real do Gemini, e a tabela mostra `Input (tokens)` / `Output (tokens)`.

---

## Checklist final

- [ ] Constantes `DEPARTMENT_NAMES`, `DEFAULT_COMPLEXITY`, `DEMO_SCENARIOS` existem fora de `main()`
- [ ] `parse_args()` valida flags juntos e faixa de `--complexity`
- [ ] `build_scenarios()` faz demo (3) ou customizado (1) e rejeita depto inválido
- [ ] `main(argv=None)` chama `parse_args` + `build_scenarios`
- [ ] `python main.py --help` lista as flags
- [ ] Demo sem args ainda funciona
- [ ] Testes `TestParseArgs` e `TestBuildScenarios` passam
- [ ] `pytest tests/ -v` verde

---

## Troubleshooting

| Problema                                | Causa provável                                                  | Solução                                                                          |
| --------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `NameError: parse_args is not defined`  | Função criada depois do `main` ou indentação errada             | Coloque `parse_args` / `build_scenarios` **no nível do módulo**, acima de `main` |
| Demo quebrou (0 cenários)               | Esqueceu de chamar `build_scenarios` ou apagou `DEMO_SCENARIOS` | Conferir Parte 1 e 4                                                             |
| `error: Use --dept e --prompt juntos`   | Passou só um flag                                               | Informe os dois                                                                  |
| `Departamento 'X' inválido`             | ID fora do YAML                                                 | Use `legal_dept`, `hr_dept` ou `it_ops`                                          |
| Teste falha com `SystemExit` inesperado | Assert sem `pytest.raises(SystemExit)`                          | Casos de erro de argparse **devem** esperar `SystemExit`                         |
| Encoding no Windows                     | Terminal cp1252                                                 | `export PYTHONIOENCODING=utf-8` antes do `python main.py`                        |

---

## Resumo do que mudou

| Antes                                   | Depois (Lab 2)                           |
| --------------------------------------- | ---------------------------------------- |
| Prompt e depto fixos no código          | Prompt e depto via `--dept` / `--prompt` |
| Sempre 3 cenários                       | Demo **ou** 1 requisição                 |
| Aluno edita `main.py` para experimentar | Aluno usa a CLI                          |

O **Router, o Gateway, a telemetria e a política YAML não mudam** — só a entrada do fluxo. Essa é a lição: quando o processamento está desacoplado da origem do dado, adicionar CLI (ou API HTTP depois) não reescreve a regra de negócio.
