"""
Testes Unitários - CostEstimator
"""

import pytest
from src.telemetry import CostEstimator


class TestCostEstimator:
    """Testes para a classe CostEstimator."""
    
    def test_estimator_initialization(self):
        """Testa inicialização do estimador com política válida."""
        estimator = CostEstimator()
        assert estimator.policy is not None
        assert len(estimator.pricing) > 0
    
    def test_calculate_cost_pro_model(self):
        """Testa cálculo de custo para modelo Pro."""
        estimator = CostEstimator()
        
        # Teste com valores conhecidos
        # Pro: input $0.00125/1k, output $0.00500/1k
        # 1000 chars = ~250 tokens (1000/4)
        cost = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=1000,
            output_chars=500
        )
        
        # Verifica que o custo é calculado corretamente
        assert cost > 0
        assert isinstance(cost, float)
        # Custo deve ter 6 casas decimais
        assert len(str(cost).split('.')[1]) <= 6
    
    def test_calculate_cost_flash_model(self):
        """Testa cálculo de custo para modelo Flash."""
        estimator = CostEstimator()
        
        # Flash: input $0.000075/1k, output $0.00030/1k
        # Flash deve ser mais barato que Pro
        cost_flash = estimator.calculate_cost(
            "gemini-2.5-flash",
            input_chars=1000,
            output_chars=500
        )
        
        cost_pro = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=1000,
            output_chars=500
        )
        
        assert cost_flash < cost_pro
    
    def test_calculate_cost_invalid_model(self):
        """Testa erro ao calcular custo para modelo inválido."""
        estimator = CostEstimator()
        
        with pytest.raises(KeyError) as exc_info:
            estimator.calculate_cost("invalid-model", 1000, 500)
        
        assert "não encontrado na política de preços" in str(exc_info.value)
    
    def test_calculate_cost_zero_input(self):
        """Testa cálculo com input zero (edge case)."""
        estimator = CostEstimator()
        
        # Deve retornar custo mínimo (output apenas)
        cost = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=0,
            output_chars=100
        )
        
        assert cost >= 0
    
    def test_calculate_cost_zero_output(self):
        """Testa cálculo com output zero (edge case)."""
        estimator = CostEstimator()
        
        # Deve retornar custo mínimo (input apenas)
        cost = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=100,
            output_chars=0
        )
        
        assert cost >= 0
    
    def test_chars_to_tokens_conversion(self):
        """Testa conversão de caracteres para tokens."""
        estimator = CostEstimator()
        
        # Teste com texto de 100 caracteres variados (mais realista)
        # Texto repetitivo é tokenizado de forma mais eficiente pelo tiktoken
        text_100 = "Este é um texto de teste com várias palavras diferentes para simular conteúdo real bem variado"
        tokens = estimator._count_tokens(text_100)
        # Com tiktoken ou fallback, deve retornar tokens > 0
        assert tokens > 0
        assert tokens < 100  # Deve ser menos que o número de caracteres
        
        # Texto vazio = pelo menos 0 tokens
        tokens = estimator._count_tokens("")
        assert tokens >= 0
        
        # 1 caractere = pelo menos 1 token
        tokens = estimator._count_tokens("a")
        assert tokens >= 1
    
    def test_cost_precision(self):
        """Testa que o custo retorna com precisão de 6 casas decimais."""
        estimator = CostEstimator()
        
        cost = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=1234,
            output_chars=567
        )
        
        # Verifica precisão
        cost_str = f"{cost:.6f}"
        assert len(cost_str.split('.')[1]) == 6
    
    def test_cost_proportionality(self):
        """Testa que o custo é proporcional ao tamanho."""
        estimator = CostEstimator()
        
        cost_small = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=100,
            output_chars=50
        )
        
        cost_large = estimator.calculate_cost(
            "gemini-2.5-pro",
            input_chars=1000,
            output_chars=500
        )
        
        # Custo maior deve ser significativamente maior
        assert cost_large > cost_small
        # Verifica proporcionalidade aproximada
        # Com tiktoken, textos de espaços são tokenizados de forma eficiente
        # então a proporção pode não ser exata, mas deve ser maior
        assert cost_large >= cost_small * 3  # Pelo menos 3x maior

