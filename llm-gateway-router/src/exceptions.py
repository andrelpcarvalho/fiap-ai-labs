"""
Exceções Customizadas - Governance Gateway
Define exceções específicas para melhor tratamento de erros
"""


class GovernanceGatewayError(Exception):
    """Exceção base para todos os erros do Governance Gateway."""
    pass


class PolicyValidationError(GovernanceGatewayError):
    """Erro ao validar política YAML."""
    pass


class PolicyNotFoundError(GovernanceGatewayError, FileNotFoundError):
    """Arquivo de política não encontrado."""
    pass


class TemplateNotFoundError(GovernanceGatewayError, FileNotFoundError):
    """Template Jinja2 não encontrado."""
    pass


class ModelNotFoundError(GovernanceGatewayError, KeyError):
    """Modelo não encontrado na política de preços."""
    pass


class DepartmentNotFoundError(GovernanceGatewayError, KeyError):
    """Departamento não encontrado na política."""
    pass


class InvalidComplexityError(GovernanceGatewayError, ValueError):
    """Score de complexidade inválido."""
    pass

