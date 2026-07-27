# Atualizando os Testes Unitários

Este guia detalha como atualizar os testes para cobrir tanto o modo mock quanto o modo real (com mocks de API).

## Visão Geral

Os testes devem:

1. Continuar funcionando sem acesso à Vertex AI
2. Testar o Gateway com mocks da API
3. Testar o novo método `calculate_cost_from_tokens()`

## Passo 1: Criar `tests/test_gateway.py`

Crie o arquivo de testes para o Gateway:

```python
"""
Testes unitários para o Gateway do Vertex AI.
Usa mocks para evitar chamadas reais à API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Importações condicionais para evitar erro se Vertex AI não instalado
try:
    from src.gateway import VertexAIGateway
    GATEWAY_AVAILABLE = True
except ImportError:
    GATEWAY_AVAILABLE = False


# Skip todos os testes se gateway não disponível
pytestmark = pytest.mark.skipif(
    not GATEWAY_AVAILABLE,
    reason="Gateway não disponível (vertexai não instalado)"
)


class TestVertexAIGatewayInit:
    """Testes de inicialização do Gateway."""

    @patch('src.gateway.vertexai')
    @patch.dict('os.environ', {
        'GOOGLE_CLOUD_PROJECT': 'test-project',
        'GOOGLE_CLOUD_LOCATION': 'us-central1'
    })
    def test_init_from_environment(self, mock_vertexai):
        """Testa inicialização a partir de variáveis de ambiente."""
        gateway = VertexAIGateway()

        assert gateway.project_id == 'test-project'
        assert gateway.location == 'us-central1'
        mock_vertexai.init.assert_called_once_with(
            project='test-project',
            location='us-central1'
        )

    @patch('src.gateway.vertexai')
    def test_init_from_parameters(self, mock_vertexai):
        """Testa inicialização a partir de parâmetros."""
        gateway = VertexAIGateway(
            project_id='param-project',
            location='europe-west1'
        )

        assert gateway.project_id == 'param-project'
        assert gateway.location == 'europe-west1'

    @patch('src.gateway.vertexai')
    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_project_raises_error(self, mock_vertexai):
        """Testa que erro é lançado sem project_id."""
        with pytest.raises(ValueError, match="project_id é obrigatório"):
            VertexAIGateway()

    @patch('src.gateway.vertexai')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_safety_settings_loaded(self, mock_vertexai):
        """Testa que safety settings são carregados do YAML."""
        gateway = VertexAIGateway()

        assert len(gateway.safety_settings) > 0


class TestVertexAIGatewayGenerate:
    """Testes de geração de respostas."""

    @patch('src.gateway.vertexai')
    @patch('src.gateway.GenerativeModel')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_generate_returns_response_and_tokens(self, mock_model_class, mock_vertexai):
        """Testa que generate retorna resposta e tokens."""
        # Configurar mock da resposta
        mock_response = MagicMock()
        mock_response.text = '{"status": "ok"}'
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        gateway = VertexAIGateway()
        response, input_tokens, output_tokens = gateway.generate(
            model_name="gemini-2.5-flash",
            prompt="Test prompt"
        )

        assert response == '{"status": "ok"}'
        assert input_tokens == 100
        assert output_tokens == 50

    @patch('src.gateway.vertexai')
    @patch('src.gateway.GenerativeModel')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_generate_audit_response_validates_with_pydantic(
        self, mock_model_class, mock_vertexai
    ):
        """Testa que generate_audit_response valida com Pydantic."""
        # Resposta válida no formato AuditResponse
        valid_response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Operação de consulta aprovada conforme políticas."
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_response)
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        gateway = VertexAIGateway()
        audit_response, input_tokens, output_tokens = gateway.generate_audit_response(
            model_name="gemini-2.5-pro",
            prompt="Test prompt"
        )

        assert audit_response.compliance_status == "APPROVED"
        assert audit_response.risk_level == "LOW"
        assert input_tokens == 100

    @patch('src.gateway.vertexai')
    @patch('src.gateway.GenerativeModel')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_generate_audit_response_invalid_json_raises_error(
        self, mock_model_class, mock_vertexai
    ):
        """Testa que JSON inválido lança erro."""
        mock_response = MagicMock()
        mock_response.text = "not valid json"
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        gateway = VertexAIGateway()

        with pytest.raises(ValueError, match="JSON inválido"):
            gateway.generate_audit_response(
                model_name="gemini-2.5-pro",
                prompt="Test prompt"
            )


class TestVertexAIGatewayModelCache:
    """Testes de cache de modelos."""

    @patch('src.gateway.vertexai')
    @patch('src.gateway.GenerativeModel')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_model_is_cached(self, mock_model_class, mock_vertexai):
        """Testa que modelos são cacheados."""
        mock_response = MagicMock()
        mock_response.text = '{"test": "ok"}'
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        gateway = VertexAIGateway()

        # Duas chamadas com o mesmo modelo
        gateway.generate("gemini-2.5-flash", "prompt 1")
        gateway.generate("gemini-2.5-flash", "prompt 2")

        # Modelo deve ser criado apenas uma vez
        assert mock_model_class.call_count == 1

    @patch('src.gateway.vertexai')
    @patch('src.gateway.GenerativeModel')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT': 'test-project'})
    def test_different_models_not_cached_together(self, mock_model_class, mock_vertexai):
        """Testa que modelos diferentes são criados separadamente."""
        mock_response = MagicMock()
        mock_response.text = '{"test": "ok"}'
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        gateway = VertexAIGateway()

        # Chamadas com modelos diferentes
        gateway.generate("gemini-2.5-flash", "prompt 1")
        gateway.generate("gemini-2.5-pro", "prompt 2")

        # Dois modelos diferentes devem ser criados
        assert mock_model_class.call_count == 2
```

## Passo 2: Atualizar `tests/test_telemetry.py`

Adicione testes para o novo método:

```python
class TestCostEstimatorFromTokens:
    """Testes para cálculo de custo com tokens reais."""

    def test_calculate_cost_from_tokens_pro(self, cost_estimator):
        """Testa cálculo de custo com tokens reais para Pro."""
        # 1000 input tokens, 500 output tokens
        cost = cost_estimator.calculate_cost_from_tokens(
            'gemini-2.5-pro',
            input_tokens=1000,
            output_tokens=500
        )

        # Pro: (1000/1000)*0.00125 + (500/1000)*0.005 = 0.00125 + 0.0025 = 0.00375
        assert cost == pytest.approx(0.00375, rel=1e-4)

    def test_calculate_cost_from_tokens_flash(self, cost_estimator):
        """Testa cálculo de custo com tokens reais para Flash."""
        cost = cost_estimator.calculate_cost_from_tokens(
            'gemini-2.5-flash',
            input_tokens=1000,
            output_tokens=500
        )

        # Flash: (1000/1000)*0.000075 + (500/1000)*0.0003 = 0.000075 + 0.00015 = 0.000225
        assert cost == pytest.approx(0.000225, rel=1e-4)

    def test_calculate_cost_from_tokens_invalid_model(self, cost_estimator):
        """Testa que modelo inválido lança erro."""
        from src.exceptions import ModelNotFoundError

        with pytest.raises(ModelNotFoundError):
            cost_estimator.calculate_cost_from_tokens(
                'modelo-inexistente',
                input_tokens=100,
                output_tokens=50
            )

    def test_calculate_cost_from_tokens_zero_tokens(self, cost_estimator):
        """Testa cálculo com zero tokens."""
        cost = cost_estimator.calculate_cost_from_tokens(
            'gemini-2.5-flash',
            input_tokens=0,
            output_tokens=0
        )

        assert cost == 0.0

    def test_calculate_cost_from_tokens_precision(self, cost_estimator):
        """Testa precisão de 6 casas decimais."""
        cost = cost_estimator.calculate_cost_from_tokens(
            'gemini-2.5-flash',
            input_tokens=1,
            output_tokens=1
        )

        # Deve ter no máximo 6 casas decimais
        cost_str = f"{cost:.10f}"
        # Verifica que após 6 casas decimais só há zeros
        assert cost_str.endswith('0000')
```

## Passo 3: Adicionar fixture se necessário

No `tests/conftest.py` ou no próprio arquivo de teste, adicione:

```python
import pytest
from src.telemetry import CostEstimator


@pytest.fixture
def cost_estimator():
    """Fixture que fornece um CostEstimator configurado."""
    return CostEstimator()
```

## Passo 4: Executar os Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Executar apenas testes do gateway
pytest tests/test_gateway.py -v

# Executar apenas testes de telemetria
pytest tests/test_telemetry.py -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html
```

## Estrutura de Testes Resultante

```
tests/
├── __init__.py
├── conftest.py             # Fixtures compartilhadas (opcional)
├── test_main.py            # Testes existentes
├── test_router.py          # Testes existentes
├── test_telemetry.py       # MODIFICADO - Novos testes
├── test_models.py          # Testes existentes
└── test_gateway.py         # NOVO - Testes do Gateway
```

## Considerações sobre Mocking

### Por que usar Mocks?

1. **Isolamento**: Testes não dependem de conexão com GCP
2. **Velocidade**: Testes executam instantaneamente
3. **Custo**: Nenhum custo de API durante testes
4. **Reprodutibilidade**: Resultados consistentes

### Estrutura de Mock da API Vertex AI

```python
# Mock da resposta do Vertex AI
mock_response = MagicMock()
mock_response.text = '{"json": "response"}'
mock_response.usage_metadata.prompt_token_count = 100  # Input tokens
mock_response.usage_metadata.candidates_token_count = 50  # Output tokens
```

## Testes de Integração (Opcional)

Para testes que fazem chamadas reais (executar manualmente):

```python
# tests/integration/test_vertex_ai_real.py
"""
Testes de integração com Vertex AI real.
ATENÇÃO: Estes testes geram custos reais!
Execute apenas manualmente: pytest tests/integration/ -v
"""

import pytest
import os

# Skip se não configurado
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "true",
    reason="Testes de integração desabilitados (RUN_INTEGRATION_TESTS != true)"
)


class TestVertexAIIntegration:
    """Testes de integração real (geram custos!)."""

    def test_real_call_flash(self):
        """Teste real com Gemini Flash."""
        from src.gateway import VertexAIGateway

        gateway = VertexAIGateway()
        response, input_tokens, output_tokens = gateway.generate(
            model_name="gemini-2.5-flash",
            prompt='Responda apenas: {"status": "ok"}',
            response_json=True
        )

        assert input_tokens > 0
        assert output_tokens > 0
        assert "status" in response
```

Executar testes de integração:

```bash
RUN_INTEGRATION_TESTS=true pytest tests/integration/ -v
```

---

**Próximo passo**: [05-verificacao-final.md](05-verificacao-final.md) - Checklist de verificação final
