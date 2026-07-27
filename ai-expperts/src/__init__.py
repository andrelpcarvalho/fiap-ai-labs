"""
Governance Gateway - Sistema de Roteamento de Modelos LLM
Padrão Router-Gateway para otimização de custos (FinOps)

Este pacote implementa um sistema de roteamento inteligente de modelos LLM
baseado em políticas configuráveis via YAML. O objetivo é demonstrar o padrão
Router-Gateway para otimização de custos (FinOps) em sistemas de IA.

Módulos Principais:
- router: Lógica de decisão de qual modelo usar (Pro vs Flash)
- telemetry: Cálculo de custos baseado em uso de tokens
- main: Script de demonstração do fluxo completo

Arquitetura:
- Desacoplamento: Política de roteamento em YAML (não no código)
- FinOps: Cálculo de custos em tempo real
- Flexibilidade: Mudanças de política sem alterar código
"""

__version__ = "1.0.0"

