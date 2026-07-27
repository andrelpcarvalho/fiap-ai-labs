"""
Configuração de Logging - Governance Gateway
Sistema de logging estruturado para rastreamento e debugging
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configura o sistema de logging do projeto.
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Caminho opcional para arquivo de log
        format_string: Formato customizado (opcional)
    
    Returns:
        Logger configurado
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    # Configurar formato
    formatter = logging.Formatter(format_string)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Criar logger raiz
    logger = logging.getLogger("governance_gateway")
    logger.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)
    
    # Handler para arquivo (se especificado)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Arquivo sempre em DEBUG
        logger.addHandler(file_handler)
    
    # Evitar propagação para logger raiz
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtém um logger para um módulo específico.
    
    Args:
        name: Nome do módulo (geralmente __name__)
    
    Returns:
        Logger configurado para o módulo
    """
    return logging.getLogger(f"governance_gateway.{name}")

