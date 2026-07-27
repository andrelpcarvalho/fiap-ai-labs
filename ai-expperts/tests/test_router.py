"""
Testes Unitários - ModelRouter
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.router import ModelRouter


class TestModelRouter:
    """Testes para a classe ModelRouter."""
    
    def test_router_initialization(self):
        """Testa inicialização do router com política válida."""
        router = ModelRouter()
        assert router.policy is not None
        assert len(router.departments) > 0
    
    def test_route_platinum_tier(self):
        """Testa roteamento para tier platinum (sempre Pro)."""
        router = ModelRouter()
        
        # Tier platinum deve sempre retornar Pro, independente da complexidade
        model = router.route_request("legal_dept", 0.1)
        assert model == "gemini-2.5-pro"
        
        model = router.route_request("legal_dept", 0.9)
        assert model == "gemini-2.5-pro"
    
    def test_route_budget_tier(self):
        """Testa roteamento para tier budget (sempre Flash)."""
        router = ModelRouter()
        
        # Tier budget deve sempre retornar Flash, independente da complexidade
        model = router.route_request("it_ops", 0.1)
        assert model == "gemini-2.5-flash"
        
        model = router.route_request("it_ops", 0.9)
        assert model == "gemini-2.5-flash"
    
    def test_route_standard_tier_low_complexity(self):
        """Testa roteamento para tier standard com complexidade baixa (Flash)."""
        router = ModelRouter()
        
        # Complexidade < threshold deve usar Flash
        model = router.route_request("hr_dept", 0.3)
        assert model == "gemini-2.5-flash"
    
    def test_route_standard_tier_high_complexity(self):
        """Testa roteamento para tier standard com complexidade alta (Pro)."""
        router = ModelRouter()
        
        # Complexidade >= threshold deve usar Pro
        model = router.route_request("hr_dept", 0.8)
        assert model == "gemini-2.5-pro"
    
    def test_route_invalid_department(self):
        """Testa erro ao usar departamento inválido."""
        router = ModelRouter()
        
        with pytest.raises(KeyError) as exc_info:
            router.route_request("invalid_dept", 0.5)
        
        assert "não encontrado na política" in str(exc_info.value)
    
    def test_route_invalid_complexity_low(self):
        """Testa erro com complexity_score abaixo do range válido."""
        router = ModelRouter()
        
        with pytest.raises(ValueError) as exc_info:
            router.route_request("hr_dept", -0.1)
        
        assert "complexity_score deve estar entre 0.0 e 1.0" in str(exc_info.value)
    
    def test_route_invalid_complexity_high(self):
        """Testa erro com complexity_score acima do range válido."""
        router = ModelRouter()
        
        with pytest.raises(ValueError) as exc_info:
            router.route_request("hr_dept", 1.5)
        
        assert "complexity_score deve estar entre 0.0 e 1.0" in str(exc_info.value)
    
    def test_route_boundary_values(self):
        """Testa valores de boundary (0.0 e 1.0)."""
        router = ModelRouter()
        
        # Deve aceitar valores de boundary
        model_low = router.route_request("hr_dept", 0.0)
        model_high = router.route_request("hr_dept", 1.0)
        
        assert model_low == "gemini-2.5-flash"  # 0.0 < 0.5
        assert model_high == "gemini-2.5-pro"   # 1.0 >= 0.5
    
    def test_route_threshold_edge_case(self):
        """Testa comportamento no threshold exato."""
        router = ModelRouter()
        
        # No threshold (0.5), deve usar Pro (>= threshold)
        model = router.route_request("hr_dept", 0.5)
        assert model == "gemini-2.5-pro"
        
        # Logo abaixo do threshold, deve usar Flash
        model = router.route_request("hr_dept", 0.499)
        assert model == "gemini-2.5-flash"


class TestModelRouterWithCustomPolicy:
    """Testes com política customizada."""
    
    def test_router_with_invalid_yaml(self):
        """Testa erro ao carregar YAML inválido."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError):
                router = ModelRouter(policy_path=temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_router_with_missing_file(self):
        """Testa erro ao carregar arquivo inexistente."""
        with pytest.raises(FileNotFoundError):
            router = ModelRouter(policy_path="config/nonexistent.yaml")

