# Lab Guiado: Conectando o Governance Gateway ao Gemini Real

> **Objetivo:** substituir a função `simulate_llm_response()` por chamadas reais aos modelos Gemini na Google Cloud (Vertex AI, hoje parte da **Gemini Enterprise Agent Platform**), mantendo toda a arquitetura Router-Gateway construída na aula.
>
> **Duração estimada:** 60–75 minutos.
>
> **⚠️ Este lab substitui os documentos `doc/01` a `doc/05`**, que foram escritos para o SDK antigo (`vertexai.generative_models`, **removido do SDK em junho/2026**) e para os modelos Gemini 1.5 (**aposentados em 2025**). Aqui usamos o SDK atual (`google-genai`) e os modelos `gemini-2.5-flash` / `gemini-2.5-pro`.

---

## Como este Lab está organizado

| Parte | Quem executa | O quê                                                     |
| ----- | ------------ | --------------------------------------------------------- |
| 1     | Aluno        | Autenticar no Google Cloud (ADC)                          |
| 2     | Aluno        | Instalar dependências e criar o `.env`                    |
| 3     | Aluno        | Atualizar os nomes de modelo (YAML, models.py, router.py) |
| 4     | Aluno        | Criar o `src/gateway.py`                                  |
| 5     | Aluno        | Ligar o gateway no `src/main.py` (flag `USE_MOCK`)        |
| 6     | Aluno        | Rodar, validar e medir custo real                         |

---

## PARTE 1 — Aluno: Autenticação no Google Cloud

> Pré-requisito: ter o [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/docs/install) instalado. No Windows, use o instalador oficial e reinicie o terminal depois.

### 1.1 Login e projeto

```bash
# 1. Login da sua conta Google (abre o navegador)
gcloud auth login

# 2. Apontar para o projeto da turma (o professor informará o ID)
gcloud config set project PROJETO_DA_TURMA
```

### 1.2 Application Default Credentials (ADC)

O SDK Python não usa o login do gcloud diretamente — usa as **ADC**, que são credenciais salvas localmente para aplicações:

```bash
gcloud auth application-default login
```

Isso abre o navegador de novo e salva um arquivo de credencial em `%APPDATA%\gcloud\application_default_credentials.json` (Windows).

### 1.3 Verificar que tudo funciona (ainda sem Python)

```bash
# Deve listar a API habilitada (habilitada pelo professor na Parte 0)
gcloud services list --enabled --filter="name:aiplatform"
```

Se aparecer `aiplatform.googleapis.com`, você está pronto. **Se der erro de permissão aqui, chame o professor** — é problema de IAM (Parte 0.3), não do seu código.

---

## PARTE 2 — Aluno: Dependências e `.env`

### 2.1 Instalar o SDK novo

```bash
# Dentro do venv do projeto
pip install google-genai python-dotenv
```

Adicione ao final do `requirements.txt`:

```text
# Google Gen AI SDK - SDK atual para chamar modelos Gemini
# (substitui vertexai.generative_models, removido em jun/2026)
google-genai>=1.0.0

# Carrega variáveis de ambiente do arquivo .env
python-dotenv>=1.0.0
```

### 2.2 Criar o arquivo `.env` na raiz do projeto

```env
# Identificação do projeto GCP (informado pelo professor)
GOOGLE_CLOUD_PROJECT=PROJETO_DA_TURMA
GOOGLE_CLOUD_LOCATION=us-central1

# true  = usa simulação (mock), sem custo — comportamento da aula
# false = chama o Gemini de verdade
USE_MOCK=true
```

**Importante:** confirme que `.env` está no `.gitignore` (credenciais e IDs de projeto não vão para o Git).

---

## PARTE 3 — Aluno: Atualizar os nomes de modelo

Os modelos `gemini-1.5-*` do projeto **não existem mais** na Google Cloud (aposentados em 2025). Vamos trocá-los por `gemini-2.5-pro` e `gemini-2.5-flash` em **três arquivos**:

### 3.1 `config/model_policy.yaml`

Substitua os nomes e atualize os preços (valores por 1k tokens; confira a [tabela oficial](https://cloud.google.com/vertex-ai/generative-ai/pricing) pois preços mudam):

```yaml
departments:
  legal_dept:
    tier: platinum
    model: gemini-2.5-pro
    complexity_threshold: null

  hr_dept:
    tier: standard
    model: null
    complexity_threshold: 0.5

  it_ops:
    tier: budget
    model: gemini-2.5-flash
    complexity_threshold: null

pricing:
  gemini-2.5-pro:
    input_per_1k_tokens: 0.00125 # US$ 1,25 / 1M tokens
    output_per_1k_tokens: 0.01000 # US$ 10,00 / 1M tokens

  gemini-2.5-flash:
    input_per_1k_tokens: 0.00030 # US$ 0,30 / 1M tokens
    output_per_1k_tokens: 0.00250 # US$ 2,50 / 1M tokens
```

### 3.2 `src/models.py`

Atualize a lista de modelos válidos no validador:

```python
valid_models = ['gemini-2.5-pro', 'gemini-2.5-flash']
```

### 3.3 `src/router.py`

O router tem os nomes **hardcoded** no método `route_request()` (uma dívida técnica proposital — boa discussão em sala!). Troque as três ocorrências:

- `model = 'gemini-2.5-pro'` → `model = 'gemini-2.5-pro'` (tiers platinum e standard-alta)
- `model = 'gemini-2.5-flash'` → `model = 'gemini-2.5-flash'` (tiers budget e standard-baixa)

### 3.4 Validar antes de continuar

```bash
python main.py
```

Deve rodar em modo simulação, agora exibindo os nomes `gemini-2.5-*`.

> Os testes em `tests/` ainda referenciam os nomes antigos — eles vão falhar. Tudo bem por enquanto; atualizá-los é o exercício final (Parte 6.3).

---

## PARTE 4 — Aluno: Criar o Gateway (`src/gateway.py`)

Este é o coração do lab: a classe que **abstrai toda a comunicação com o Gemini**. Crie o arquivo `src/gateway.py`:

```python
"""
Gateway de comunicação com os modelos Gemini (Google Cloud).

Padrão Router-Gateway:
- O Router (router.py) DECIDE qual modelo usar.
- O Gateway (este arquivo) EXECUTA a chamada, sem saber por que
  o modelo foi escolhido.

SDK: google-genai (o SDK antigo vertexai.generative_models foi
removido em jun/2026). Autenticação via ADC:
    gcloud auth application-default login
"""

import os
from pathlib import Path
from typing import Tuple, List, Optional

import yaml
from google import genai
from google.genai import types

from .models import AuditResponse
from .logger import get_logger

logger = get_logger(__name__)


class VertexAIGateway:
    """
    Balcão único de acesso aos modelos Gemini.

    Responsabilidades:
    1. Autenticar e criar o cliente (uma vez, no __init__)
    2. Aplicar safety settings carregados do YAML (padrão ADK)
    3. Forçar saída JSON no schema AuditResponse
    4. Devolver a contagem REAL de tokens (FinOps preciso)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        safety_path: str = "config/safety_settings.yaml",
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not self.project_id:
            raise ValueError(
                "project_id é obrigatório. Defina GOOGLE_CLOUD_PROJECT no .env "
                "ou passe project_id no construtor."
            )

        # Cliente do Google Gen AI SDK apontando para a plataforma
        # (vertexai=True usa o endpoint do projeto GCP, com ADC — sem API key)
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
        )

        self.safety_settings = self._load_safety_settings(safety_path)

        logger.info(
            f"Gateway inicializado: project={self.project_id}, "
            f"location={self.location}"
        )

    def _load_safety_settings(self, safety_path: str) -> List[types.SafetySetting]:
        """Carrega config/safety_settings.yaml e converte para o formato do SDK."""
        project_root = Path(__file__).parent.parent
        full_path = project_root / safety_path

        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        settings = [
            types.SafetySetting(
                category=item["category"],
                threshold=item["threshold"],
            )
            for item in data.get("safety_settings", [])
        ]
        logger.debug(f"{len(settings)} safety settings carregados do YAML")
        return settings

    def generate_audit_response(
        self, model_name: str, prompt: str
    ) -> Tuple[AuditResponse, int, int]:
        """
        Chama o modelo e devolve (resposta_validada, input_tokens, output_tokens).

        - response_mime_type + response_schema garantem JSON no formato
          do AuditResponse (o modelo é FORÇADO a seguir o schema).
        - usage_metadata devolve tokens EXATOS cobrados pela API
          (fim das estimativas com tiktoken).
        """
        logger.info(f"Chamada real ao modelo: {model_name}")

        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=AuditResponse,
                safety_settings=self.safety_settings,
            ),
        )

        # Validação Pydantic: se o JSON fugir do contrato, explode AQUI
        audit = AuditResponse.model_validate_json(response.text)

        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count

        logger.info(
            f"Resposta recebida: {audit.compliance_status} | "
            f"tokens: {input_tokens} in / {output_tokens} out"
        )
        return audit, input_tokens, output_tokens
```

**Pontos para discutir com a turma:**

1. `genai.Client(vertexai=True, ...)` — nenhuma API key no código. A autenticação vem das ADC feitas na Parte 1. Credencial no código = incidente de segurança.
2. `response_schema=AuditResponse` — o mesmo modelo Pydantic da aula agora **força** o Gemini a responder no formato certo (isso se chama _controlled generation_ / _structured output_).
3. `usage_metadata` — os tokens agora são os **reais**, cobrados pela fatura. O tiktoken vira apenas estimativa pré-chamada.

---

## PARTE 5 — Aluno: Ligar o Gateway no `main.py`

### 5.1 Custo a partir de tokens reais (`src/telemetry.py`)

O `CostEstimator.calculate_cost()` recebe **caracteres** e estima tokens. Com a API real já temos tokens exatos — adicione este método à classe `CostEstimator`:

```python
    def calculate_cost_from_tokens(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calcula custo a partir de tokens REAIS retornados pela API
        (usage_metadata). Sem estimativa: este é o valor da fatura.
        """
        if model_name not in self.pricing:
            raise ModelNotFoundError(
                f"Modelo '{model_name}' não encontrado na política de preços"
            )

        model_pricing = self.pricing[model_name]
        input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
        output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens

        cost = round(input_cost + output_cost, 6)
        logger.info(f"Custo REAL: ${cost:.6f} USD para {model_name}")
        return cost
```

### 5.2 Modificações no `src/main.py`

**(a)** No topo do arquivo, após os imports existentes:

```python
import os
from dotenv import load_dotenv

load_dotenv()  # carrega o .env da raiz do projeto

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
```

**(b)** Dentro da função `main()`, logo após criar `router` e `cost_estimator`, inicialize o gateway (somente em modo real):

```python
    gateway = None
    if not USE_MOCK:
        try:
            from .gateway import VertexAIGateway
            gateway = VertexAIGateway()
            console.print("[bold green]Modo REAL: chamadas ao Gemini via Google Cloud[/bold green]\n")
        except Exception as e:
            logger.error(f"Falha ao iniciar gateway: {e}", exc_info=True)
            console.print(f"[bold red]Gateway indisponível ({e}). Caindo para modo simulação.[/bold red]\n")
    else:
        console.print("[dim]Modo SIMULAÇÃO (USE_MOCK=true): nenhuma chamada real, custo zero[/dim]\n")
```

**(c)** No loop de cenários, substitua o bloco do **Passo 2** (chamada `simulate_llm_response`) e do **Passo 3** (cálculo de custo) por:

```python
        # Passo 2: Chamada ao LLM (real ou simulada)
        if gateway is not None:
            prompt = render_prompt_template(scenario['user_request'])
            try:
                audit, input_tokens, output_tokens = gateway.generate_audit_response(
                    selected_model, prompt
                )
                mock_response = audit.model_dump()
            except Exception as e:
                logger.error(f"Erro na chamada real: {e}", exc_info=True)
                console.print(f"[bold red]Erro na chamada ao Gemini: {e}[/bold red]")
                continue

            # Passo 3: custo com tokens REAIS da API
            estimated_cost = cost_estimator.calculate_cost_from_tokens(
                selected_model, input_tokens, output_tokens
            )
            input_chars, output_chars = input_tokens, output_tokens  # p/ exibição
        else:
            mock_response = simulate_llm_response(
                selected_model, scenario['user_request']
            )
            input_chars, output_chars = simulate_input_output(
                scenario['user_request'], mock_response
            )
            estimated_cost = cost_estimator.calculate_cost(
                selected_model, input_chars, output_chars
            )
```

> Nota: quando em modo real, as colunas "Input/Output (chars)" da tabela passam a exibir **tokens** — se quiser, renomeie os rótulos da tabela para "Input (tokens)"/"Output (tokens)".

---

## PARTE 6 — Rodar, Validar e Medir

### 6.1 Primeiro em simulação (garante que nada quebrou)

```bash
# .env com USE_MOCK=true
python main.py
```

### 6.2 Agora de verdade

Edite o `.env`: `USE_MOCK=false`. Rode de novo:

```bash
python main.py
```

**O que observar (e comentar em sala):**

1. A mensagem `Modo REAL` no início.
2. O `audit_reasoning` agora é um **texto genuíno do Gemini**, diferente a cada execução — compare com as frases fixas do mock.
3. Os tokens são os **reais** da API — repare que o número difere da estimativa do tiktoken.
4. O custo do cenário 1 (Jurídico → `gemini-2.5-pro`) é visivelmente maior que os cenários 2 e 3 (`gemini-2.5-flash`). **O FinOps saiu da teoria.**

### 6.3 Exercício final: consertar os testes

Os testes antigos referenciam `gemini-1.5-*`. Atualize `tests/test_router.py`, `tests/test_models.py` e `tests/test_main.py` para os nomes novos e rode:

```bash
pytest tests/ -v
```

_(Para testar o `gateway.py` sem gastar dinheiro, use `unittest.mock.patch` no `genai.Client` — o `doc/04-atualizando-testes.md` tem a estratégia geral de mocks, apenas adapte os alvos do patch para `src.gateway.genai`.)_

---

## Troubleshooting (erros mais comuns na turma)

| Erro                                                           | Causa provável                                                | Solução                                                                                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `403 SERVICE_DISABLED` / "API has not been used in project..." | API não habilitada no projeto                                 | **Professor** habilita (Parte 0.2). Aluno não tem privilégio para isso — não adianta tentar `gcloud services enable`. |
| `403 PERMISSION_DENIED` ao chamar o modelo                     | Aluno sem `roles/aiplatform.user`                             | **Professor** concede o papel (Parte 0.3)                                                                             |
| `PERMISSION_DENIED` mencionando _quota project_                | Falta `roles/serviceusage.serviceUsageConsumer`               | Professor concede o papel; aluno roda `gcloud auth application-default login` de novo                                 |
| `Your default credentials were not found`                      | ADC não configurado                                           | `gcloud auth application-default login` (Parte 1.2)                                                                   |
| `404 NOT_FOUND` para o modelo                                  | Nome de modelo antigo (`gemini-1.5-*`) ou região sem o modelo | Conferir Parte 3; testar `GOOGLE_CLOUD_LOCATION=global`                                                               |
| `ModuleNotFoundError: google.genai`                            | SDK não instalado no venv ativo                               | `pip install google-genai` com o venv ativado                                                                         |
| `ValidationError` do Pydantic na resposta                      | Resposta fora do schema (raro com `response_schema`)          | Verificar se `response_schema=AuditResponse` está no `GenerateContentConfig`                                          |
| Billing error mesmo com API habilitada                         | Projeto sem billing vinculado                                 | **Professor** vincula billing account ao projeto                                                                      |

---

## Resumo do que mudou em relação à aula

| Componente       | Aula (simulação)                   | Lab (real)                                    |
| ---------------- | ---------------------------------- | --------------------------------------------- |
| Resposta do LLM  | `if/elif` de palavras-chave        | Gemini real via `google-genai`                |
| Modelos          | `gemini-1.5-*` (strings fictícias) | `gemini-2.5-pro` / `gemini-2.5-flash`         |
| Tokens           | Estimados com tiktoken             | Exatos, da `usage_metadata`                   |
| JSON estruturado | Dicionário montado à mão           | `response_schema` força o formato             |
| Safety settings  | Arquivo decorativo                 | Aplicados de verdade em cada chamada          |
| Autenticação     | Nenhuma                            | ADC (`gcloud auth application-default login`) |
| Custo            | Zero                               | Real (centavos — mas real!)                   |

O **Router, a política YAML, a telemetria e o Pydantic não mudaram** — essa é a lição da arquitetura: quando a escolha do modelo está desacoplada, trocar o "motor" (mock → API real) não toca na regra de negócio.
