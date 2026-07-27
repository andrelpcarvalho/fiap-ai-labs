# Criando o Gateway para Vertex AI

Este guia detalha a criação do módulo `gateway.py` que fará chamadas reais à API do Vertex AI.

## Visão Geral

O Gateway é o componente responsável por:

- Inicializar conexão com Vertex AI
- Enviar prompts aos modelos Gemini
- Retornar respostas estruturadas + contagem de tokens reais

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   main.py   │ ──▶ │  gateway.py │ ──▶ │  Vertex AI  │
│ (orquestra) │     │  (conexão)  │     │   (API)     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Passo 1: Criar o arquivo `src/gateway.py`

Crie o arquivo `src/gateway.py` com o seguinte conteúdo:

```python
"""
Gateway para Vertex AI - Integração Real
Responsável por fazer chamadas à API do Vertex AI e retornar respostas estruturadas.

Este módulo substitui a simulação (mock) por chamadas reais aos modelos Gemini,
permitindo obter tokens reais para cálculo preciso de custos (FinOps).
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold
)

from .models import AuditResponse
from .exceptions import PolicyNotFoundError
from .logger import get_logger

logger = get_logger(__name__)


class VertexAIGateway:
    """
    Gateway para comunicação com a API do Vertex AI.

    Esta classe encapsula toda a lógica de comunicação com o Vertex AI,
    incluindo inicialização, configuração de safety settings e chamadas
    aos modelos Gemini.

    Attributes:
        project_id: ID do projeto Google Cloud
        location: Região do Vertex AI (ex: us-central1)
        safety_settings: Configurações de segurança carregadas do YAML
    """

    # Mapeamento de categorias de harm (YAML -> SDK)
    HARM_CATEGORY_MAP = {
        "HARM_CATEGORY_HARASSMENT": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "HARM_CATEGORY_HATE_SPEECH": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "HARM_CATEGORY_DANGEROUS_CONTENT": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    }

    # Mapeamento de thresholds (YAML -> SDK)
    THRESHOLD_MAP = {
        "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
        "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
        "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    }

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        safety_settings_path: str = "config/safety_settings.yaml"
    ):
        """
        Inicializa o gateway com configurações do Vertex AI.

        Args:
            project_id: ID do projeto GCP. Se None, usa GOOGLE_CLOUD_PROJECT
            location: Região do Vertex AI. Se None, usa GOOGLE_CLOUD_LOCATION
            safety_settings_path: Caminho para o arquivo YAML de safety settings
        """
        # Carregar configurações de ambiente ou parâmetros
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not self.project_id:
            raise ValueError(
                "project_id é obrigatório. Defina GOOGLE_CLOUD_PROJECT ou passe como parâmetro."
            )

        logger.info(f"Inicializando Vertex AI: project={self.project_id}, location={self.location}")

        # Inicializar Vertex AI SDK
        vertexai.init(project=self.project_id, location=self.location)

        # Carregar safety settings
        self.safety_settings = self._load_safety_settings(safety_settings_path)

        # Cache de modelos inicializados
        self._models: Dict[str, GenerativeModel] = {}

        logger.info("Gateway Vertex AI inicializado com sucesso")

    def _load_safety_settings(self, config_path: str) -> List[SafetySetting]:
        """
        Carrega safety settings do arquivo YAML.

        Args:
            config_path: Caminho relativo para o arquivo YAML

        Returns:
            Lista de SafetySetting configurados
        """
        project_root = Path(__file__).parent.parent
        full_path = project_root / config_path

        try:
            logger.debug(f"Carregando safety settings de: {full_path}")
            with open(full_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"Arquivo de safety settings não encontrado: {full_path}")
            raise PolicyNotFoundError(f"Safety settings não encontrado: {full_path}") from e

        settings = []
        for item in config.get("safety_settings", []):
            category = self.HARM_CATEGORY_MAP.get(item["category"])
            threshold = self.THRESHOLD_MAP.get(item["threshold"])

            if category and threshold:
                settings.append(SafetySetting(
                    category=category,
                    threshold=threshold
                ))
                logger.debug(f"Safety setting carregado: {item['category']} -> {item['threshold']}")

        logger.info(f"Carregadas {len(settings)} configurações de segurança")
        return settings

    def _get_model(self, model_name: str) -> GenerativeModel:
        """
        Obtém ou cria uma instância do modelo.

        Usa cache para evitar reinicialização desnecessária.

        Args:
            model_name: Nome do modelo (ex: gemini-2.5-pro)

        Returns:
            Instância do GenerativeModel
        """
        if model_name not in self._models:
            logger.debug(f"Inicializando modelo: {model_name}")
            self._models[model_name] = GenerativeModel(
                model_name=model_name,
                safety_settings=self.safety_settings
            )
        return self._models[model_name]

    def generate(
        self,
        model_name: str,
        prompt: str,
        response_json: bool = True,
        temperature: float = 0.1
    ) -> Tuple[str, int, int]:
        """
        Gera resposta usando o modelo especificado.

        Args:
            model_name: Nome do modelo a usar
            prompt: Prompt completo a enviar
            response_json: Se True, força resposta em JSON
            temperature: Temperatura do modelo (0.0 = determinístico)

        Returns:
            Tupla (resposta_texto, input_tokens, output_tokens)
        """
        logger.info(f"Gerando resposta com {model_name}")

        model = self._get_model(model_name)

        # Configuração de geração
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=1024,
        )

        # Adicionar mime type JSON se solicitado
        if response_json:
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=0.95,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )

        try:
            # Fazer chamada à API
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Extrair tokens REAIS da resposta
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count

            logger.info(f"Resposta recebida: {input_tokens} input tokens, {output_tokens} output tokens")

            return response.text, input_tokens, output_tokens

        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}", exc_info=True)
            raise

    def generate_audit_response(
        self,
        model_name: str,
        prompt: str
    ) -> Tuple[AuditResponse, int, int]:
        """
        Gera resposta de auditoria validada com Pydantic.

        Este método garante que a resposta do modelo está no formato
        esperado (AuditResponse) através de validação Pydantic.

        Args:
            model_name: Nome do modelo a usar
            prompt: Prompt completo formatado

        Returns:
            Tupla (AuditResponse validado, input_tokens, output_tokens)

        Raises:
            ValidationError: Se a resposta não puder ser validada
        """
        response_text, input_tokens, output_tokens = self.generate(
            model_name=model_name,
            prompt=prompt,
            response_json=True
        )

        # Validar resposta com Pydantic
        try:
            response_dict = json.loads(response_text)
            audit_response = AuditResponse(**response_dict)
            logger.debug("Resposta validada com sucesso via Pydantic")
            return audit_response, input_tokens, output_tokens
        except json.JSONDecodeError as e:
            logger.error(f"Resposta não é JSON válido: {response_text[:100]}...")
            raise ValueError(f"Modelo retornou JSON inválido: {e}") from e
```

## Passo 2: Adicionar exceção customizada

Edite o arquivo `src/exceptions.py` e adicione (se não existir):

```python
class GatewayError(Exception):
    """Erro na comunicação com Vertex AI."""
    pass
```

## Passo 3: Exportar o Gateway no `__init__.py`

Edite `src/__init__.py` e adicione:

```python
from .gateway import VertexAIGateway
```

## Estrutura de Arquivos Resultante

```
src/
├── __init__.py          # Exporta VertexAIGateway
├── gateway.py           # NOVO - Gateway para Vertex AI
├── main.py              # Orquestrador
├── router.py            # Roteamento de modelos
├── telemetry.py         # Cálculo de custos
├── models.py            # Modelos Pydantic
├── exceptions.py        # Exceções customizadas
└── logger.py            # Sistema de logging
```

## Testando o Gateway

Crie um script de teste rápido:

```python
# test_gateway_quick.py
from src.gateway import VertexAIGateway

# Inicializar (usa variáveis de ambiente)
gateway = VertexAIGateway()

# Teste simples
response, input_tokens, output_tokens = gateway.generate(
    model_name="gemini-2.5-flash",
    prompt="Responda em JSON: {\"status\": \"ok\", \"message\": \"teste\"}",
    response_json=True
)

print(f"Resposta: {response}")
print(f"Input tokens: {input_tokens}")
print(f"Output tokens: {output_tokens}")
```

Execute:

```bash
python test_gateway_quick.py
```

## Diagrama de Sequência

```
┌──────────┐     ┌─────────────┐     ┌────────────┐     ┌───────────┐
│  main.py │     │  gateway.py │     │ Vertex AI  │     │  Pydantic │
└────┬─────┘     └──────┬──────┘     └─────┬──────┘     └─────┬─────┘
     │                  │                  │                  │
     │ generate_audit() │                  │                  │
     │─────────────────▶│                  │                  │
     │                  │                  │                  │
     │                  │ generate_content │                  │
     │                  │─────────────────▶│                  │
     │                  │                  │                  │
     │                  │  response + tokens                  │
     │                  │◀─────────────────│                  │
     │                  │                  │                  │
     │                  │ validate()       │                  │
     │                  │─────────────────────────────────────▶
     │                  │                  │                  │
     │                  │ AuditResponse    │                  │
     │                  │◀─────────────────────────────────────
     │                  │                  │                  │
     │ (response, tokens)                  │                  │
     │◀─────────────────│                  │                  │
     │                  │                  │                  │
```

---

**Próximo passo**: [03-atualizando-main.md](03-atualizando-main.md) - Integrar o gateway no fluxo principal
