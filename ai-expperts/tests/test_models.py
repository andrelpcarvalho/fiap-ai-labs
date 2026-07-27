"""
Testes Unitários - Modelos Pydantic
"""

import pytest
from pydantic import ValidationError

from src.models import (
    PricingModel,
    DepartmentConfig,
    ModelPolicy,
    AuditResponse
)


class TestPricingModel:
    """Testes para o modelo PricingModel."""
    
    def test_valid_pricing_model(self):
        """Testa criação de modelo de preços válido."""
        pricing = PricingModel(
            input_per_1k_tokens=0.00125,
            output_per_1k_tokens=0.00500
        )
        
        assert pricing.input_per_1k_tokens == 0.00125
        assert pricing.output_per_1k_tokens == 0.00500
    
    def test_pricing_model_negative_input(self):
        """Testa erro com preço negativo."""
        with pytest.raises(ValidationError):
            PricingModel(
                input_per_1k_tokens=-0.001,
                output_per_1k_tokens=0.005
            )
    
    def test_pricing_model_zero_input(self):
        """Testa erro com preço zero."""
        with pytest.raises(ValidationError):
            PricingModel(
                input_per_1k_tokens=0.0,
                output_per_1k_tokens=0.005
            )


class TestDepartmentConfig:
    """Testes para o modelo DepartmentConfig."""
    
    def test_valid_platinum_tier(self):
        """Testa configuração válida de tier platinum."""
        dept = DepartmentConfig(
            tier="platinum",
            model="gemini-2.5-pro",
            complexity_threshold=None
        )
        
        assert dept.tier == "platinum"
        assert dept.model == "gemini-2.5-pro"
    
    def test_valid_standard_tier(self):
        """Testa configuração válida de tier standard."""
        dept = DepartmentConfig(
            tier="standard",
            model=None,
            complexity_threshold=0.5
        )
        
        assert dept.tier == "standard"
        assert dept.complexity_threshold == 0.5
    
    def test_standard_tier_missing_threshold(self):
        """Testa erro quando tier standard não tem threshold."""
        with pytest.raises(ValidationError) as exc_info:
            DepartmentConfig(
                tier="standard",
                model=None,
                complexity_threshold=None
            )
        
        assert "complexity_threshold" in str(exc_info.value)
    
    def test_invalid_tier(self):
        """Testa erro com tier inválido."""
        with pytest.raises(ValidationError):
            DepartmentConfig(
                tier="invalid",
                model=None
            )
    
    def test_invalid_threshold_range(self):
        """Testa erro com threshold fora do range."""
        with pytest.raises(ValidationError):
            DepartmentConfig(
                tier="standard",
                complexity_threshold=1.5  # Fora do range [0.0, 1.0]
            )


class TestModelPolicy:
    """Testes para o modelo ModelPolicy."""
    
    def test_valid_policy(self):
        """Testa criação de política válida."""
        policy_data = {
            "departments": {
                "legal_dept": {
                    "tier": "platinum",
                    "model": "gemini-2.5-pro",
                    "complexity_threshold": None
                }
            },
            "pricing": {
                "gemini-2.5-pro": {
                    "input_per_1k_tokens": 0.00125,
                    "output_per_1k_tokens": 0.00500
                }
            }
        }
        
        policy = ModelPolicy(**policy_data)
        assert len(policy.departments) == 1
        assert len(policy.pricing) == 1
    
    def test_invalid_model_name(self):
        """Testa erro com nome de modelo inválido."""
        policy_data = {
            "departments": {},
            "pricing": {
                "invalid-model": {
                    "input_per_1k_tokens": 0.001,
                    "output_per_1k_tokens": 0.005
                }
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ModelPolicy(**policy_data)
        
        assert "não é suportado" in str(exc_info.value)


class TestAuditResponse:
    """Testes para o modelo AuditResponse."""
    
    def test_valid_audit_response(self):
        """Testa criação de resposta de auditoria válida."""
        response = AuditResponse(
            compliance_status="APPROVED",
            risk_level="LOW",
            audit_reasoning="Operação de baixo risco aprovada."
        )
        
        assert response.compliance_status == "APPROVED"
        assert response.risk_level == "LOW"
        assert len(response.audit_reasoning) >= 10
    
    def test_invalid_compliance_status(self):
        """Testa erro com status de compliance inválido."""
        with pytest.raises(ValidationError):
            AuditResponse(
                compliance_status="INVALID",
                risk_level="LOW",
                audit_reasoning="Teste"
            )
    
    def test_invalid_risk_level(self):
        """Testa erro com nível de risco inválido."""
        with pytest.raises(ValidationError):
            AuditResponse(
                compliance_status="APPROVED",
                risk_level="INVALID",
                audit_reasoning="Teste"
            )
    
    def test_short_reasoning(self):
        """Testa erro com reasoning muito curto."""
        with pytest.raises(ValidationError):
            AuditResponse(
                compliance_status="APPROVED",
                risk_level="LOW",
                audit_reasoning="Curto"  # Menos de 10 caracteres
            )

