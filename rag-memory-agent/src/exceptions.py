# Exceção base para todo o sistema de memória (Short-Term e Long-Term)
# Todas as outras exceções do módulo herdam dela para tratamento centralizado
class MemorySystemError(Exception):
    """Base exception for the memory system."""

    pass


# Erro quando o estado da sessão está inválido ou corrompido (ex.: checkpoint com dados inesperados)
# Permite que o código detecte e trate (ex.: resetar para estado inicial) de forma controlada
class StateValidationError(MemorySystemError):
    """Raised when the session state is invalid or corrupted."""

    pass


# Erro ao carregar um checkpoint (ex.: falha de rede, serviço indisponível)
# Usado quando não é possível recuperar a sessão e pode ser necessário fallback ou recriação
class SessionRecoveryError(MemorySystemError):
    """Raised when a checkpoint fails to load and fallback is required."""

    pass


# Erro quando a Memória de Longo Prazo (Vertex AI Vector Search) está indisponível
# Permite degradação graciosa: continuar sem contexto RAG em vez de quebrar o fluxo
class VectorSearchError(MemorySystemError):
    """Raised when the Long-Term Memory (Vertex Search) is unavailable."""

    pass


# Erro de Concorrência Otimista (OCC): outra escrita salvou o checkpoint antes desta
# O campo version no estado permite detectar conflitos e evitar sobrescrever dados
class ConcurrentWriteError(MemorySystemError):
    """Raised when OCC detects a version conflict (another writer saved the checkpoint)."""

    pass
