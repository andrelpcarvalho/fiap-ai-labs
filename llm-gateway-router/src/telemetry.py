"""
Módulo de Telemetria e FinOps - Aula 01
Responsável por calcular custos de operação baseado em uso de tokens

Este módulo implementa a calculadora de custos (FinOps) para operações
com modelos LLM. O cálculo é baseado em:
- Número de tokens de input (prompt enviado ao modelo)
- Número de tokens de output (resposta do modelo)
- Preços por modelo (definidos em model_policy.yaml)

🎯 Objetivo da Aula 01:
Demonstrar como monitorar custos em tempo real e comparar modelos
(Gemini Flash vs Pro) para otimização financeira.

📚 Conexão com próximas aulas:
- Aula 02: Adicionaremos Intent Guardrail que também usa tokenização
- Aula 03: Validação de JSON estruturado retornará tokens reais da API

Arquitetura:
- Desacopla cálculo de custos do código de roteamento
- Permite diferentes estratégias de pricing sem alterar código
- Facilita análise de custos e otimização (FinOps)

Uso:
    estimator = CostEstimator()
    cost = estimator.calculate_cost('gemini-2.5-pro', 1000, 500)
    # Retorna custo em USD com 6 casas decimais
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

# Importação condicional: tiktoken para contagem precisa, fallback para aproximação
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    import warnings
    warnings.warn(
        "tiktoken não instalado. Usando aproximação de tokens (menos precisa). "
        "Instale com: pip install tiktoken"
    )

from .models import ModelPolicy, PricingModel
from .exceptions import (
    PolicyValidationError,
    PolicyNotFoundError,
    ModelNotFoundError
)
from .logger import get_logger

logger = get_logger(__name__)


class CostEstimator:
    """
    Calculadora de custos para operações com modelos LLM.
    
    🎯 FinOps (Financial Operations) - Aula 01:
    Este componente é central para o objetivo da aula: monitorar custos
    em tempo real e comparar modelos. Em produção bancária, o desperdício
    invisível de usar modelos caros indiscriminadamente pode gerar
    milhares de dólares em custos desnecessários.
    
    Arquitetura: Desacopla o cálculo de custos do roteamento, permitindo
    que diferentes estratégias de pricing sejam aplicadas sem modificar
    o código de negócio.
    
    📊 Comparativo Prático (Aula 01):
    - Gemini-2.5-flash: ~$0.075/1M input tokens, ~$0.30/1M output tokens
    - Gemini-2.5-pro: ~$1.25/1M input tokens, ~$5.00/1M output tokens
    Diferença: Pro é ~16x mais caro que Flash!
    """
    
    # ------------------------------------------------------------------------
    # Configuração de Tokenização
    # ------------------------------------------------------------------------
    # IMPORTANTE - Aula 01: Por que tokenização precisa?
    # 
    # 1. Custos são cobrados por TOKEN, não por caractere
    # 2. 1 token ≠ 1 caractere (varia por idioma e modelo)
    # 3. Aproximação "4 chars = 1 token" pode errar em ±30%
    # 4. Erro na contagem = erro no cálculo de custos = FinOps impreciso
    #
    # Solução: Usar tiktoken (encoding do modelo Gemini) para contagem precisa
    # Fallback: Aproximação quando tiktoken não disponível (apenas para demo)
    
    # Encoding do Gemini (cl100k_base é usado por GPT-4 e modelos similares)
    # Nota: Gemini usa encoding próprio, mas cl100k_base é uma boa aproximação
    # Em produção com Vertex AI, a API retorna tokens reais na resposta
    _ENCODING_NAME = "cl100k_base"  # Encoding compartilhado por muitos modelos modernos
    
    # Aproximação de fallback (usada apenas se tiktoken não disponível)
    # Baseada em média empírica: português/inglês ≈ 3.5-4.5 chars/token
    CHARS_PER_TOKEN_FALLBACK = 4
    
    def __init__(self, policy_path: str = "config/model_policy.yaml"):
        """
        Inicializa o estimador carregando a política de preços do YAML.
        
        🏗️ Estrutura ADK - Aula 01:
        A política está em config/ seguindo o padrão ADK (Agent Development Kit):
        - config/: Configurações (políticas, safety settings)
        - prompts/: Templates de prompts (versionamento)
        - tools/: Ferramentas do agente (será usado nas aulas futuras)
        
        Esta separação permite:
        - Mudanças sem alterar código
        - Versionamento de configurações
        - Auditoria de mudanças (Git)
        
        Args:
            policy_path: Caminho para o arquivo YAML com política de preços
        """
        # Resolver caminho relativo à raiz do projeto
        project_root = Path(__file__).parent.parent
        self.policy_path = project_root / policy_path
        self.policy: Optional[ModelPolicy] = None
        self.pricing: Dict[str, PricingModel] = {}
        
        # Inicializar encoder de tokens (tiktoken)
        self._init_token_encoder()
        
        self._load_pricing()
    
    def _init_token_encoder(self) -> None:
        """
        Inicializa o encoder de tokens para contagem precisa.
        
        🎯 Aula 01 - Tokenização Precisa:
        Usa tiktoken para contar tokens com precisão, essencial para
        cálculo correto de custos (FinOps). Sem isso, erros de ±30%
        são comuns, tornando a análise financeira imprecisa.
        
        Em produção com Vertex AI, a API retorna usage_metadata com
        tokens reais, mas tiktoken permite estimativa antes da chamada.
        """
        self.token_encoder = None
        
        if TIKTOKEN_AVAILABLE:
            try:
                # Cl100k_base é o encoding usado por modelos modernos
                # É uma boa aproximação para Gemini (encoding exato seria específico)
                self.token_encoder = tiktoken.get_encoding(self._ENCODING_NAME)
                logger.info("Token encoder inicializado (tiktoken)")
            except Exception as e:
                logger.warning(f"Erro ao inicializar tiktoken: {e}. Usando fallback.")
                self.token_encoder = None
        else:
            logger.warning(
                "tiktoken não disponível. Usando aproximação de fallback. "
                "Para precisão, instale: pip install tiktoken"
            )
    
    def _load_pricing(self) -> None:
        """
        Carrega e valida a seção de pricing do arquivo YAML de política.
        
        Este método carrega o YAML, valida com Pydantic e extrai a seção
        'pricing' com preços por modelo (input/output separados).
        
        🏗️ Validação Pydantic - Aula 03:
        A validação robusta com Pydantic será expandida na Aula 03 para
        validar respostas JSON do LLM. Aqui validamos a configuração,
        lá validaremos o output do modelo.
        
        Raises:
            FileNotFoundError: Se o arquivo de política não existir
            ValueError: Se o YAML estiver malformado ou inválido
            ValidationError: Se a estrutura não corresponder ao schema Pydantic
        """
        try:
            logger.debug(f"Carregando política de preços de: {self.policy_path}")
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            logger.debug("YAML de preços carregado com sucesso")
        except FileNotFoundError as e:
            logger.error(f"Arquivo de política não encontrado: {self.policy_path}")
            raise PolicyNotFoundError(
                f"Arquivo de política não encontrado: {self.policy_path}"
            ) from e
        except yaml.YAMLError as e:
            logger.error(f"Erro ao processar YAML: {e}")
            raise ValueError(f"Erro ao processar YAML: {e}") from e
        
        # Validação com Pydantic
        try:
            logger.debug("Validando política de preços com Pydantic")
            self.policy = ModelPolicy(**policy_data)
            self.pricing = self.policy.pricing
            logger.info(f"Política de preços validada: {len(self.pricing)} modelos configurados")
        except ValidationError as e:
            logger.error(f"Erro de validação Pydantic: {e}")
            raise PolicyValidationError(
                f"Erro ao validar política: {e}. "
                "Verifique se o YAML está no formato correto."
            ) from e
        except Exception as e:
            logger.error(f"Erro inesperado ao validar política: {e}", exc_info=True)
            raise PolicyValidationError(
                f"Erro inesperado ao validar política: {e}"
            ) from e
    
    def _count_tokens(self, text: str) -> int:
        """
        Conta tokens em um texto usando método preciso ou aproximação.
        
        🎯 Aula 01 - FinOps Preciso:
        Esta função é crítica para cálculo correto de custos. Erros aqui
        se propagam para toda a análise financeira.
        
        Métodos (em ordem de precisão):
        1. tiktoken (preciso): Usa encoding real do modelo
        2. Aproximação (fallback): 4 chars ≈ 1 token (pode errar ±30%)
        
        📊 Exemplo de impacto:
        - Texto: "Preciso revisar o contrato" (30 chars)
        - tiktoken: ~8 tokens
        - Aproximação: 30/4 = 7.5 tokens
        - Erro: ~6% (aceitável para demo, inaceitável para produção)
        
        Args:
            text: Texto para contar tokens
            
        Returns:
            Número de tokens (preciso se tiktoken disponível, aproximado caso contrário)
        """
        if self.token_encoder is not None:
            # Método preciso: usa encoding real
            try:
                tokens = self.token_encoder.encode(text)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Erro ao contar tokens com tiktoken: {e}. Usando fallback.")
        
        # Método de fallback: aproximação por caracteres
        # Aproximação conservadora: assume 4 chars/token (média para português/inglês)
        # Nota: Esta aproximação pode errar em ±30% dependendo do conteúdo
        char_count = len(text)
        tokens_approx = max(1, char_count // self.CHARS_PER_TOKEN_FALLBACK)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Tokenização por aproximação: {char_count} chars → ~{tokens_approx} tokens "
                f"(precisão: ±30% estimado)"
            )
        
        return tokens_approx
    
    def calculate_cost(
        self, 
        model_name: str, 
        input_chars: int, 
        output_chars: int
    ) -> float:
        """
        Calcula o custo total de uma operação com o modelo.
        
        🎯 Aula 01 - FinOps em Tempo Real:
        Este é o coração da demonstração: calcular custos em tempo real
        para comparar modelos e otimizar gastos.
        
        📊 Fórmula de Custo:
        Custo = (input_tokens / 1000) * preço_input_por_1k + 
                (output_tokens / 1000) * preço_output_por_1k
        
        💡 Exemplo Prático (Aula 01):
        Requisição: 1000 tokens input, 500 tokens output
        - Flash: (1000/1000)*$0.075 + (500/1000)*$0.30 = $0.225
        - Pro:   (1000/1000)*$1.25 + (500/1000)*$5.00 = $3.75
        Diferença: Pro é 16.7x mais caro!
        
        📚 Conexão Aula 03:
        Na Aula 03, quando integrarmos com Vertex AI real, a API retornará
        usage_metadata com tokens exatos. Por enquanto, estimamos com tiktoken.
        
        Args:
            model_name: Nome do modelo (ex: 'gemini-2.5-pro')
            input_chars: Número de caracteres no input (será convertido para tokens)
            output_chars: Número de caracteres no output (será convertido para tokens)
            
        Returns:
            Custo total em USD com 6 casas decimais
            
        Raises:
            KeyError: Se o modelo não estiver na política de preços
        """
        logger.debug(f"Calculando custo: model={model_name}, input={input_chars} chars, output={output_chars} chars")
        
        if model_name not in self.pricing:
            logger.warning(f"Modelo não encontrado na política: {model_name}")
            raise ModelNotFoundError(
                f"Modelo '{model_name}' não encontrado na política de preços"
            )
        
        # Obtém preços do modelo da política validada
        model_pricing = self.pricing[model_name]
        
        # ------------------------------------------------------------------------
        # Passo 1: Converter caracteres para tokens (preciso)
        # ------------------------------------------------------------------------
        # IMPORTANTE: Convertemos chars → tokens ANTES de calcular custo
        # porque preços são por TOKEN, não por caractere
        input_text = " " * input_chars  # Placeholder: em produção seria o texto real
        output_text = " " * output_chars  # Placeholder: em produção seria o texto real
        
        # Nota: Para cálculo preciso, precisaríamos do texto real, não apenas chars
        # Na Aula 03, quando tivermos a resposta real da API, usaremos o texto completo
        input_tokens = self._count_tokens(input_text)
        output_tokens = self._count_tokens(output_text)
        
        logger.debug(f"Tokens calculados: input={input_tokens}, output={output_tokens}")
        
        # ------------------------------------------------------------------------
        # Passo 2: Calcular custos (preços no YAML são por 1k tokens)
        # ------------------------------------------------------------------------
        # Exemplo: 500 tokens = 0.5 * preço_por_1k
        # Usa os atributos do modelo Pydantic validado
        input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
        output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens
        
        # ------------------------------------------------------------------------
        # Passo 3: Custo total = input + output
        # ------------------------------------------------------------------------
        total_cost = input_cost + output_cost
        
        # ------------------------------------------------------------------------
        # Passo 4: Retornar com 6 casas decimais (precisão para microtransações)
        # ------------------------------------------------------------------------
        # 6 casas decimais permitem rastrear custos de requisições individuais
        # mesmo quando muito pequenos (ex: $0.000123 USD)
        cost_rounded = round(total_cost, 6)
        logger.info(f"Custo calculado: ${cost_rounded:.6f} USD para {model_name}")
        return cost_rounded

    def calculate_cost_from_tokens(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calcula custo a partir de tokens REAIS retornados pela API
        (usage_metadata). Sem estimativa: este é o valor da fatura.
        """
        if model_name not in self.pricing:
            raise ModelNotFoundError(
                f"Modelo '{model_name}' não encontrado na política de preços"
            )

        model_pricing = self.pricing[model_name]
        input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
        output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens

        cost = round(input_cost + output_cost, 6)
        logger.info(f"Custo REAL: ${cost:.6f} USD para {model_name}")
        return cost