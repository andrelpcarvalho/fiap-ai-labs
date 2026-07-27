# Documentação: Integração com Vertex AI

Esta pasta contém o tutorial completo para integrar o Governance Gateway com a API real do Google Cloud Vertex AI.

## Índice dos Documentos

| #   | Documento                                            | Descrição                             |
| --- | ---------------------------------------------------- | ------------------------------------- |
| 1   | [01-configuracao-gcp.md](01-configuracao-gcp.md)     | Configuração do Google Cloud Platform |
| 2   | [02-criando-gateway.md](02-criando-gateway.md)       | Criação do módulo Gateway             |
| 3   | [03-atualizando-main.md](03-atualizando-main.md)     | Modificações no main.py               |
| 4   | [04-atualizando-testes.md](04-atualizando-testes.md) | Atualização dos testes                |
| 5   | [05-verificacao-final.md](05-verificacao-final.md)   | Checklist de verificação              |

## Ordem de Execução Recomendada

```
┌─────────────────────┐
│ 01-configuracao-gcp │  Configurar GCP e autenticação
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 02-criando-gateway  │  Criar src/gateway.py
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 03-atualizando-main │  Modificar src/main.py e telemetry.py
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 04-atualizando-testes│ Criar/atualizar testes
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 05-verificacao-final│  Validar implementação
└─────────────────────┘
```

## Pré-requisitos

Antes de iniciar, certifique-se de ter:

- Python 3.8+ instalado
- Conta Google Cloud Platform
- Acesso à internet para instalação de dependências

## Tempo Estimado

| Etapa            | Tempo          |
| ---------------- | -------------- |
| Configuração GCP | 15-20 min      |
| Criar Gateway    | 10-15 min      |
| Atualizar Main   | 15-20 min      |
| Atualizar Testes | 10-15 min      |
| Verificação      | 5-10 min       |
| **Total**        | **~60-80 min** |

## Resultado Final

Após completar o tutorial, o sistema terá:

1. **Dois modos de operação**:
   - `USE_MOCK=true`: Simulação (sem custos)
   - `USE_MOCK=false`: Vertex AI real

2. **Tokens reais** da API do Vertex AI

3. **Cálculo preciso de custos** (FinOps)

4. **Testes atualizados** com mocks adequados

## Quick Start (Resumo)

```bash
# 1. Configurar GCP
gcloud auth application-default login
gcloud config set project SEU_PROJETO
gcloud services enable aiplatform.googleapis.com

# 2. Configurar ambiente
cp .env.example .env
# Editar .env com suas configurações

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Testar em modo mock
USE_MOCK=true python main.py

# 5. Testar em modo real
USE_MOCK=false python main.py
```

## Suporte

Em caso de problemas, consulte a seção de Troubleshooting em [05-verificacao-final.md](05-verificacao-final.md).
