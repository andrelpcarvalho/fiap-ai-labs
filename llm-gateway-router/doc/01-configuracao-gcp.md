# Configuração do Google Cloud Platform

Este guia detalha os passos necessários para configurar o ambiente Google Cloud antes de integrar o Governance Gateway com a Vertex AI.

## Pré-requisitos

- Conta Google Cloud Platform (GCP) ativa
- Cartão de crédito vinculado (para billing, mesmo com free tier)
- Google Cloud CLI (`gcloud`) instalado

## Passo 1: Instalar o Google Cloud CLI

### Windows (PowerShell como Administrador)

```powershell
# Download do instalador
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")

# Executar instalador
& $env:Temp\GoogleCloudSDKInstaller.exe
```

Ou baixe diretamente: https://cloud.google.com/sdk/docs/install

### Linux/macOS

```bash
# Linux (Debian/Ubuntu)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# macOS (com Homebrew)
brew install --cask google-cloud-sdk
```

### Verificar instalação

```bash
gcloud version
```

## Passo 2: Criar ou Selecionar um Projeto

### Opção A: Criar novo projeto

```bash
# Criar projeto (substitua pelo seu ID único)
gcloud projects create meu-projeto-vertex-ai --name="Governance Gateway"

# Definir como projeto ativo
gcloud config set project meu-projeto-vertex-ai
```

### Opção B: Usar projeto existente

```bash
# Listar projetos disponíveis
gcloud projects list

# Selecionar projeto
gcloud config set project SEU_PROJECT_ID
```

## Passo 3: Habilitar Billing

O Vertex AI requer billing habilitado. Acesse:

1. https://console.cloud.google.com/billing
2. Vincule uma conta de faturamento ao projeto
3. Verifique se o projeto está vinculado:

```bash
gcloud beta billing projects describe $(gcloud config get-value project)
```

## Passo 4: Habilitar a API do Vertex AI

```bash
# Habilitar Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Verificar se foi habilitada
gcloud services list --enabled | grep aiplatform
```

Saída esperada:

```
aiplatform.googleapis.com    Vertex AI API
```

## Passo 5: Configurar Autenticação (ADC)

O SDK Python usa Application Default Credentials (ADC) para autenticação automática.

```bash
# Fazer login e configurar ADC
gcloud auth application-default login
```

Este comando:

1. Abre o navegador para autenticação Google
2. Salva as credenciais em:
   - Windows: `%APPDATA%\gcloud\application_default_credentials.json`
   - Linux/macOS: `~/.config/gcloud/application_default_credentials.json`

### Verificar autenticação

```bash
gcloud auth application-default print-access-token
```

Se retornar um token (string longa), a autenticação está funcionando.

## Passo 6: Definir Região

Escolha uma região próxima para menor latência:

| Região               | Localização       | Recomendado para                    |
| -------------------- | ----------------- | ----------------------------------- |
| `us-central1`        | Iowa, EUA         | Uso geral, mais modelos disponíveis |
| `southamerica-east1` | São Paulo, Brasil | Menor latência para Brasil          |
| `europe-west1`       | Bélgica           | Europa                              |

```bash
# Definir região padrão
gcloud config set compute/region us-central1
```

## Passo 7: Verificar Configuração Final

```bash
# Verificar todas as configurações
gcloud config list

# Saída esperada:
# [core]
# account = seu-email@gmail.com
# project = meu-projeto-vertex-ai
#
# [compute]
# region = us-central1
```

## Passo 8: Testar Acesso à Vertex AI

Teste rápido via CLI para garantir que tudo está funcionando:

```bash
# Listar modelos disponíveis (deve retornar lista)
gcloud ai models list --region=us-central1 2>/dev/null || echo "OK - Nenhum modelo customizado (normal)"
```

## Variáveis de Ambiente

Após configurar, defina as variáveis que o Governance Gateway usará:

### Windows (PowerShell)

```powershell
$env:GOOGLE_CLOUD_PROJECT = "meu-projeto-vertex-ai"
$env:GOOGLE_CLOUD_LOCATION = "us-central1"
```

### Linux/macOS

```bash
export GOOGLE_CLOUD_PROJECT="meu-projeto-vertex-ai"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Custos Estimados

| Modelo           | Input (1M tokens) | Output (1M tokens) |
| ---------------- | ----------------- | ------------------ |
| Gemini 1.5 Flash | ~$0.075           | ~$0.30             |
| Gemini 1.5 Pro   | ~$1.25            | ~$5.00             |

Para uma demonstração típica (3 requisições):

- **Flash**: ~$0.0001 USD
- **Pro**: ~$0.001 USD

Consulte preços atualizados: https://cloud.google.com/vertex-ai/generative-ai/pricing

## Troubleshooting

### Erro: "Permission denied"

```bash
# Verificar se a API está habilitada
gcloud services list --enabled | grep aiplatform

# Se não aparecer, habilitar novamente
gcloud services enable aiplatform.googleapis.com
```

### Erro: "Could not automatically determine credentials"

```bash
# Refazer autenticação ADC
gcloud auth application-default login
```

### Erro: "Billing not enabled"

1. Acesse https://console.cloud.google.com/billing
2. Vincule conta de faturamento ao projeto

---

**Próximo passo**: [02-criando-gateway.md](02-criando-gateway.md) - Criar o módulo de integração com Vertex AI
