# Atualizando o Main para Usar o Gateway

Este guia detalha as modificações necessárias no `src/main.py` para integrar o Gateway do Vertex AI.

## Visão Geral das Mudanças

O arquivo `src/main.py` será modificado para:

1. Suportar modo **mock** (atual) e modo **real** (Vertex AI)
2. Usar tokens reais da API quando em modo real
3. Carregar configurações de variáveis de ambiente

## Passo 1: Criar arquivo `.env`

Na raiz do projeto, crie o arquivo `.env`:

```env
# Configurações do Google Cloud
GOOGLE_CLOUD_PROJECT=seu-projeto-id
GOOGLE_CLOUD_LOCATION=us-central1

# Modo de operação: true = simulação, false = Vertex AI real
USE_MOCK=true
```

Crie também `.env.example` (para versionamento):

```env
# Configurações do Google Cloud
GOOGLE_CLOUD_PROJECT=seu-projeto-id
GOOGLE_CLOUD_LOCATION=us-central1

# Modo de operação: true = simulação, false = Vertex AI real
USE_MOCK=true
```

## Passo 2: Atualizar `requirements.txt`

Adicione a dependência `python-dotenv`:

```
# Adicionar ao final do requirements.txt
python-dotenv>=1.0.0
```

Instale:

```bash
pip install python-dotenv
```

## Passo 3: Modificar `src/main.py`

### 3.1 Adicionar imports no início do arquivo

Localize a seção de imports (linhas 40-54) e adicione:

```python
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
```

### 3.2 Adicionar import condicional do Gateway

Após os imports existentes, adicione:

```python
# Import condicional do Gateway (evita erro se Vertex AI não configurado)
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

if not USE_MOCK:
    try:
        from .gateway import VertexAIGateway
        GATEWAY_AVAILABLE = True
    except ImportError as e:
        import warnings
        warnings.warn(f"Gateway não disponível: {e}. Usando modo mock.")
        GATEWAY_AVAILABLE = False
        USE_MOCK = True
else:
    GATEWAY_AVAILABLE = False
```

### 3.3 Criar função para chamada real ao LLM

Adicione esta nova função após `simulate_llm_response()`:

```python
def call_vertex_ai(
    gateway: "VertexAIGateway",
    model_name: str,
    user_request: str
) -> tuple[dict, int, int]:
    """
    Faz chamada real ao Vertex AI e retorna resposta com tokens.

    Esta função substitui simulate_llm_response() quando USE_MOCK=false.
    Usa o gateway para fazer chamadas reais à API do Vertex AI.

    Args:
        gateway: Instância do VertexAIGateway inicializado
        model_name: Nome do modelo (ex: 'gemini-2.5-pro')
        user_request: Solicitação do usuário

    Returns:
        Tupla (resposta_dict, input_tokens, output_tokens)
    """
    # Renderizar prompt completo
    prompt = render_prompt_template(user_request)

    # Fazer chamada ao Vertex AI
    audit_response, input_tokens, output_tokens = gateway.generate_audit_response(
        model_name=model_name,
        prompt=prompt
    )

    # Converter Pydantic para dict
    response_dict = {
        "compliance_status": audit_response.compliance_status,
        "risk_level": audit_response.risk_level,
        "audit_reasoning": audit_response.audit_reasoning
    }

    return response_dict, input_tokens, output_tokens
```

### 3.4 Modificar a função `main()`

Substitua a função `main()` por esta versão atualizada:

```python
def main():
    """
    Função principal de demonstração.

    Suporta dois modos de operação:
    - USE_MOCK=true: Simulação (sem chamadas reais, sem custos)
    - USE_MOCK=false: Vertex AI real (chamadas reais, custos reais)
    """
    # Configurar logging para a aplicação
    setup_logging(level="INFO")
    logger.info("Iniciando Governance Gateway - Demonstração")

    console = Console()

    # Título com indicação do modo
    mode_indicator = "[yellow](MOCK)[/yellow]" if USE_MOCK else "[green](VERTEX AI)[/green]"

    console.print("\n")
    console.print(
        Panel.fit(
            f"[bold cyan]Governance Gateway[/bold cyan] {mode_indicator}\n"
            "[dim]Sistema de Roteamento de Modelos LLM - Padrão Router-Gateway[/dim]",
            border_style="cyan"
        )
    )
    console.print("\n")

    # ------------------------------------------------------------------------
    # Inicialização dos Componentes
    # ------------------------------------------------------------------------
    try:
        logger.info("Inicializando componentes: ModelRouter e CostEstimator")
        router = ModelRouter()
        cost_estimator = CostEstimator()

        # Inicializar Gateway se em modo real
        gateway = None
        if not USE_MOCK and GATEWAY_AVAILABLE:
            logger.info("Inicializando VertexAIGateway (modo real)")
            gateway = VertexAIGateway()
            console.print("[green]✓ Conectado ao Vertex AI[/green]\n")
        else:
            console.print("[yellow]⚠ Modo simulação ativo (USE_MOCK=true)[/yellow]\n")

        logger.info("Componentes inicializados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar componentes: {e}", exc_info=True)
        console.print(f"[bold red]Erro ao inicializar componentes: {e}[/bold red]")
        return

    # ------------------------------------------------------------------------
    # Cenários de Teste
    # ------------------------------------------------------------------------
    scenarios = [
        {
            "department": "legal_dept",
            "department_name": "Departamento Jurídico",
            "user_request": "Preciso revisar o contrato de parceria com a empresa XYZ para verificar cláusulas de confidencialidade",
            "complexity": 0.8
        },
        {
            "department": "hr_dept",
            "department_name": "Recursos Humanos",
            "user_request": "Verificar saldo de férias do funcionário ID 12345",
            "complexity": 0.3
        },
        {
            "department": "it_ops",
            "department_name": "Operações de TI",
            "user_request": "Consultar logs de acesso do sistema de gestão",
            "complexity": 0.2
        }
    ]

    # ------------------------------------------------------------------------
    # Processamento de Cada Cenário
    # ------------------------------------------------------------------------
    for idx, scenario in enumerate(scenarios, 1):
        console.print(f"\n[bold yellow]━━━ Cenário {idx}: {scenario['department_name']} ━━━[/bold yellow]\n")

        # Passo 1: Roteamento
        try:
            logger.info(f"Processando cenário {idx}: {scenario['department_name']}")
            selected_model = router.route_request(
                scenario['department'],
                scenario['complexity']
            )
            logger.debug(f"Modelo selecionado: {selected_model}")
        except Exception as e:
            logger.error(f"Erro no roteamento para {scenario['department']}: {e}", exc_info=True)
            console.print(f"[bold red]Erro no roteamento: {e}[/bold red]")
            continue

        # Passo 2: Chamada ao LLM (mock ou real)
        try:
            if USE_MOCK or gateway is None:
                # Modo simulação
                mock_response = simulate_llm_response(
                    selected_model,
                    scenario['user_request']
                )
                input_chars, output_chars = simulate_input_output(
                    scenario['user_request'],
                    mock_response
                )
                # Calcular custo com estimativa de tokens
                estimated_cost = cost_estimator.calculate_cost(
                    selected_model,
                    input_chars,
                    output_chars
                )
                input_tokens = None
                output_tokens = None
            else:
                # Modo real - Vertex AI
                mock_response, input_tokens, output_tokens = call_vertex_ai(
                    gateway,
                    selected_model,
                    scenario['user_request']
                )
                # Calcular custo com tokens REAIS
                estimated_cost = cost_estimator.calculate_cost_from_tokens(
                    selected_model,
                    input_tokens,
                    output_tokens
                )
        except Exception as e:
            logger.error(f"Erro na chamada ao LLM: {e}", exc_info=True)
            console.print(f"[bold red]Erro na chamada ao LLM: {e}[/bold red]")
            continue

        # Passo 3: Exibição de Resultados
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Atributo", style="cyan", width=25)
        table.add_column("Valor", style="white")

        table.add_row("Departamento", scenario['department_name'])
        table.add_row("Complexidade", f"{scenario['complexity']:.2f}")
        table.add_row("Modelo Escolhido", f"[bold green]{selected_model}[/bold green]")
        table.add_row("Custo Estimado", f"[bold yellow]${estimated_cost:.6f} USD[/bold yellow]")

        # Mostrar tokens (reais ou estimados)
        if input_tokens is not None:
            table.add_row("Input Tokens", f"{input_tokens} [green](real)[/green]")
            table.add_row("Output Tokens", f"{output_tokens} [green](real)[/green]")
        else:
            table.add_row("Input (chars)", f"{input_chars} [yellow](estimado)[/yellow]")
            table.add_row("Output (chars)", f"{output_chars} [yellow](estimado)[/yellow]")

        console.print(table)

        # Exibir resposta do auditor
        console.print("\n[bold]Resposta do Auditor:[/bold]")
        console.print(JSON(json.dumps(mock_response, ensure_ascii=False, indent=2)))
        console.print("\n")

    # ------------------------------------------------------------------------
    # Resumo Final
    # ------------------------------------------------------------------------
    logger.info("Demonstração concluída com sucesso")

    if USE_MOCK:
        status_msg = "[bold yellow]✓ Demonstração concluída (modo simulação)[/bold yellow]"
    else:
        status_msg = "[bold green]✓ Demonstração concluída (Vertex AI real)[/bold green]"

    console.print(
        Panel.fit(
            f"{status_msg}\n"
            "[dim]O sistema demonstrou o roteamento baseado em política YAML[/dim]",
            border_style="green"
        )
    )
    console.print("\n")
```

## Passo 4: Atualizar `src/telemetry.py`

Adicione o método `calculate_cost_from_tokens()` na classe `CostEstimator`:

```python
def calculate_cost_from_tokens(
    self,
    model_name: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Calcula o custo total usando tokens REAIS (não estimados).

    Este método é usado quando temos tokens reais da API do Vertex AI,
    permitindo cálculo preciso de custos.

    Args:
        model_name: Nome do modelo (ex: 'gemini-2.5-pro')
        input_tokens: Número real de tokens de input (da API)
        output_tokens: Número real de tokens de output (da API)

    Returns:
        Custo total em USD com 6 casas decimais
    """
    logger.debug(f"Calculando custo (tokens reais): model={model_name}, input={input_tokens}, output={output_tokens}")

    if model_name not in self.pricing:
        logger.warning(f"Modelo não encontrado na política: {model_name}")
        raise ModelNotFoundError(
            f"Modelo '{model_name}' não encontrado na política de preços"
        )

    model_pricing = self.pricing[model_name]

    # Cálculo direto com tokens reais (sem conversão)
    input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
    output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens

    total_cost = input_cost + output_cost
    cost_rounded = round(total_cost, 6)

    logger.info(f"Custo calculado (tokens reais): ${cost_rounded:.6f} USD para {model_name}")
    return cost_rounded
```

## Resultado Final

Após todas as modificações:

```bash
# Modo simulação (padrão)
USE_MOCK=true python main.py

# Modo Vertex AI real
USE_MOCK=false python main.py
```

## Estrutura de Arquivos Atualizada

```
governance-gateway/
├── .env                    # NOVO - Variáveis de ambiente (local)
├── .env.example            # NOVO - Template para .env
├── main.py                 # Ponto de entrada
├── requirements.txt        # Atualizado com python-dotenv
│
├── src/
│   ├── __init__.py         # Exporta VertexAIGateway
│   ├── gateway.py          # NOVO - Gateway Vertex AI
│   ├── main.py             # MODIFICADO - Suporta mock/real
│   ├── telemetry.py        # MODIFICADO - Novo método
│   └── ...
```

## Testando a Integração

### Teste 1: Modo Mock (sem custos)

```bash
# Certifique-se de que USE_MOCK=true no .env
python main.py
```

Saída esperada: Mesma saída atual com indicador "(MOCK)"

### Teste 2: Modo Real (com custos)

```bash
# Configure USE_MOCK=false no .env
# Certifique-se de que GOOGLE_CLOUD_PROJECT está correto
python main.py
```

Saída esperada: Tokens reais e indicador "(VERTEX AI)"

---

**Próximo passo**: [04-atualizando-testes.md](04-atualizando-testes.md) - Atualizar testes unitários
