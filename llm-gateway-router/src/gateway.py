"""
Gateway de comunicação com os modelos Gemini (Google Cloud).

Padrão Router-Gateway:
- O Router (router.py) DECIDE qual modelo usar.
- O Gateway (este arquivo) EXECUTA a chamada, sem saber por que
  o modelo foi escolhido.

SDK: google-genai (o SDK antigo vertexai.generative_models foi
removido em jun/2026). Autenticação via ADC:
    gcloud auth application-default login
"""

import os
from pathlib import Path
from typing import Tuple, List, Optional

import yaml
from google import genai
from google.genai import types

from .models import AuditResponse
from .logger import get_logger

logger = get_logger(__name__)


class VertexAIGateway:
    """
    Balcão único de acesso aos modelos Gemini.

    Responsabilidades:
    1. Autenticar e criar o cliente (uma vez, no __init__)
    2. Aplicar safety settings carregados do YAML (padrão ADK)
    3. Forçar saída JSON no schema AuditResponse
    4. Devolver a contagem REAL de tokens (FinOps preciso)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        safety_path: str = "config/safety_settings.yaml",
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not self.project_id:
            raise ValueError(
                "project_id é obrigatório. Defina GOOGLE_CLOUD_PROJECT no .env "
                "ou passe project_id no construtor."
            )

        # Cliente do Google Gen AI SDK apontando para a plataforma
        # (vertexai=True usa o endpoint do projeto GCP, com ADC — sem API key)
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
        )

        self.safety_settings = self._load_safety_settings(safety_path)

        logger.info(
            f"Gateway inicializado: project={self.project_id}, "
            f"location={self.location}"
        )

    def _load_safety_settings(self, safety_path: str) -> List[types.SafetySetting]:
        """Carrega config/safety_settings.yaml e converte para o formato do SDK."""
        project_root = Path(__file__).parent.parent
        full_path = project_root / safety_path

        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        settings = [
            types.SafetySetting(
                category=item["category"],
                threshold=item["threshold"],
            )
            for item in data.get("safety_settings", [])
        ]
        logger.debug(f"{len(settings)} safety settings carregados do YAML")
        return settings

    def generate_audit_response(
        self, model_name: str, prompt: str
    ) -> Tuple[AuditResponse, int, int]:
        """
        Chama o modelo e devolve (resposta_validada, input_tokens, output_tokens).

        - response_mime_type + response_schema garantem JSON no formato
          do AuditResponse (o modelo é FORÇADO a seguir o schema).
        - usage_metadata devolve tokens EXATOS cobrados pela API
          (fim das estimativas com tiktoken).
        """
        logger.info(f"Chamada real ao modelo: {model_name}")

        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=AuditResponse,
                safety_settings=self.safety_settings,
            ),
        )

        # Validação Pydantic: se o JSON fugir do contrato, explode AQUI
        audit = AuditResponse.model_validate_json(response.text)

        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count

        logger.info(
            f"Resposta recebida: {audit.compliance_status} | "
            f"tokens: {input_tokens} in / {output_tokens} out"
        )
        return audit, input_tokens, output_tokens