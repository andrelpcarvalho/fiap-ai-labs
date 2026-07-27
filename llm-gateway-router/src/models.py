"""
Modelos Pydantic para Validação de Dados
Valida estruturas YAML e respostas do LLM
"""

from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Modelos de Configuração (YAML)
# ============================================================================

class PricingModel(BaseModel):
    """Modelo de preços para um modelo LLM."""
    input_per_1k_tokens: float = Field(gt=0, description="Preço por 1k tokens de input")
    output_per_1k_tokens: float = Field(gt=0, description="Preço por 1k tokens de output")


class DepartmentConfig(BaseModel):
    """Configuração de um departamento na política de roteamento."""
    tier: Literal["platinum", "standard", "budget"] = Field(
        description="Tier do departamento"
    )
    model: Optional[str] = Field(
        default=None,
        description="Modelo fixo (se None, decisão baseada em complexidade)"
    )
    complexity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Threshold de complexidade para tier standard"
    )
    
    @field_validator('complexity_threshold')
    @classmethod
    def validate_threshold_for_standard(cls, v, info):
        """Valida que tier standard tem threshold definido."""
        tier = info.data.get('tier')
        if tier == 'standard' and v is None:
            raise ValueError("Tier 'standard' requer complexity_threshold definido")
        return v


class ModelPolicy(BaseModel):
    """Política completa de roteamento de modelos."""
    departments: Dict[str, DepartmentConfig] = Field(
        description="Configurações por departamento"
    )
    pricing: Dict[str, PricingModel] = Field(
        description="Preços por modelo"
    )
    
    @field_validator('pricing')
    @classmethod
    def validate_model_names(cls, v):
        """Valida que os nomes de modelos são válidos."""
        valid_models = ['gemini-2.5-pro', 'gemini-2.5-flash']
        for model_name in v.keys():
            if model_name not in valid_models:
                raise ValueError(
                    f"Modelo '{model_name}' não é suportado. "
                    f"Modelos válidos: {valid_models}"
                )
        return v


# ============================================================================
# Modelos de Resposta do LLM
# ============================================================================

class AuditResponse(BaseModel):
    """Resposta estruturada do auditor de governança."""
    compliance_status: Literal["APPROVED", "REJECTED", "REQUIRES_REVIEW"] = Field(
        description="Status de compliance da solicitação"
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Nível de risco identificado"
    )
    audit_reasoning: str = Field(
        min_length=10,
        description="Justificativa detalhada da análise"
    )

