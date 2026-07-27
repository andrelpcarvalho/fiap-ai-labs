"""
Testes Unitários - Funções do main.py
"""

import pytest
from pathlib import Path
from src.main import render_prompt_template, simulate_llm_response, simulate_input_output

from src.main import (
    render_prompt_template,
    simulate_llm_response,
    simulate_input_output,
    parse_args,
    build_scenarios,
)

from src.router import ModelRouter

class TestPromptTemplate:
    """Testes para processamento de templates Jinja2."""
    
    def test_render_prompt_template(self):
        """Testa renderização de template Jinja2."""
        user_request = "Teste de solicitação"
        prompt = render_prompt_template(user_request)
        
        # Verifica que o prompt foi processado
        assert len(prompt) > 0
        # Verifica que a solicitação do usuário está no prompt
        assert user_request in prompt
        # Verifica que não há placeholders não substituídos
        assert "{{ user_request }}" not in prompt
    
    def test_render_prompt_template_with_special_chars(self):
        """Testa renderização com caracteres especiais."""
        user_request = "Teste com 'aspas' e \"aspas duplas\""
        prompt = render_prompt_template(user_request)
        
        assert user_request in prompt
    
    def test_render_prompt_template_missing_file(self):
        """Testa erro com arquivo de template inexistente."""
        # Jinja2 pode lançar TemplateNotFound ou ValueError
        with pytest.raises((FileNotFoundError, ValueError)):
            render_prompt_template("teste", "prompts/nonexistent.jinja2")


class TestSimulateLLMResponse:
    """Testes para simulação de resposta do LLM."""
    
    def test_simulate_llm_response_transfer(self):
        """Testa simulação de resposta para transferência."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Preciso fazer uma transferência"
        )
        
        assert "compliance_status" in response
        assert "risk_level" in response
        assert "audit_reasoning" in response
        assert response["compliance_status"] == "REQUIRES_REVIEW"
    
    def test_simulate_llm_response_consultation(self):
        """Testa simulação de resposta para consulta."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Consultar saldo"
        )
        
        assert response["compliance_status"] == "APPROVED"
        assert response["risk_level"] == "LOW"
    
    def test_simulate_llm_response_deletion(self):
        """Testa simulação de resposta para exclusão."""
        # Testa com diferentes variações da palavra exclusão
        for request in ["Excluir dados", "exclusão de registros", "delete files", "remover dados"]:
            response = simulate_llm_response(
                "gemini-2.5-pro",
                request
            )
            
            assert response["compliance_status"] == "REJECTED"
            assert response["risk_level"] == "HIGH"
    
    def test_simulate_llm_response_pro_vs_flash(self):
        """Testa diferença entre respostas Pro e Flash."""
        response_pro = simulate_llm_response(
            "gemini-2.5-pro",
            "Consulta genérica"
        )
        
        response_flash = simulate_llm_response(
            "gemini-2.5-flash",
            "Consulta genérica"
        )
        
        # Pro deve ter reasoning mais longo
        assert len(response_pro["audit_reasoning"]) > len(response_flash["audit_reasoning"])


class TestSimulateInputOutput:
    """Testes para simulação de input/output."""
    
    def test_simulate_input_output(self):
        """Testa cálculo de tamanho de input/output."""
        user_request = "Teste de solicitação"
        model_response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Teste de reasoning"
        }
        
        input_chars, output_chars = simulate_input_output(user_request, model_response)
        
        assert input_chars > 0
        assert output_chars > 0
        # Input deve incluir o template + request
        assert input_chars > len(user_request)
        # Output deve incluir o JSON da resposta
        assert output_chars > 0
    
    def test_simulate_input_output_proportional(self):
        """Testa que tamanhos são proporcionais."""
        short_request = "Curto"
        long_request = "Esta é uma solicitação muito mais longa com mais detalhes"
        
        response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Teste"
        }
        
        input_short, _ = simulate_input_output(short_request, response)
        input_long, _ = simulate_input_output(long_request, response)
        
        assert input_long > input_short

class TestParseArgs:
    """Testes para parse_args (Lab 2 — CLI)."""

    def test_parse_args_no_args(self):
        args = parse_args([])
        assert args.department is None
        assert args.user_request is None
        assert args.complexity is None

    def test_parse_args_dept_and_prompt(self):
        args = parse_args([
            "--dept", "hr_dept",
            "--prompt", "Verificar saldo de férias",
        ])
        assert args.department == "hr_dept"
        assert args.user_request == "Verificar saldo de férias"
        assert args.complexity is None

    def test_parse_args_with_complexity(self):
        args = parse_args([
            "--dept", "legal_dept",
            "--prompt", "Revisar NDA",
            "--complexity", "0.9",
        ])
        assert args.complexity == 0.9

    def test_parse_args_only_dept_raises(self):
        with pytest.raises(SystemExit):
            parse_args(["--dept", "hr_dept"])

    def test_parse_args_only_prompt_raises(self):
        with pytest.raises(SystemExit):
            parse_args(["--prompt", "Algo"])

    def test_parse_args_invalid_complexity_raises(self):
        with pytest.raises(SystemExit):
            parse_args([
                "--dept", "hr_dept",
                "--prompt", "Teste",
                "--complexity", "1.5",
            ])

class TestBuildScenarios:
    """Testes para build_scenarios (Lab 2 — CLI)."""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_build_scenarios_demo(self, router):
        args = parse_args([])
        scenarios = build_scenarios(args, router)
        assert len(scenarios) == 3
        assert scenarios[0]["department"] == "legal_dept"
        assert scenarios[1]["department"] == "hr_dept"
        assert scenarios[2]["department"] == "it_ops"

    def test_build_scenarios_custom(self, router):
        args = parse_args([
            "--dept", "it_ops",
            "--prompt", "Consultar logs do sistema",
        ])
        scenarios = build_scenarios(args, router)
        assert len(scenarios) == 1
        assert scenarios[0]["department"] == "it_ops"
        assert scenarios[0]["user_request"] == "Consultar logs do sistema"
        assert scenarios[0]["department_name"] == "Operações de TI"
        assert scenarios[0]["complexity"] == 0.2

    def test_build_scenarios_default_complexity_by_dept(self, router):
        for dept, expected in [
            ("legal_dept", 0.8),
            ("hr_dept", 0.3),
            ("it_ops", 0.2),
        ]:
            args = parse_args(["--dept", dept, "--prompt", "teste"])
            scenarios = build_scenarios(args, router)
            assert scenarios[0]["complexity"] == expected

    def test_build_scenarios_custom_complexity(self, router):
        args = parse_args([
            "--dept", "hr_dept",
            "--prompt", "Análise complexa de folha",
            "--complexity", "0.7",
        ])
        scenarios = build_scenarios(args, router)
        assert scenarios[0]["complexity"] == 0.7

    def test_build_scenarios_invalid_department(self, router):
        args = parse_args([
            "--dept", "marketing_dept",
            "--prompt", "Campanha",
        ])
        with pytest.raises(ValueError) as exc_info:
            build_scenarios(args, router)
        assert "inválido" in str(exc_info.value)