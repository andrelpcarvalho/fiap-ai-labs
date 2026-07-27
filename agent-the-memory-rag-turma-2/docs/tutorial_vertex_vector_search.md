# Tutorial: Vertex AI Vector Search — do zero ao índice e endpoint no GCP

Este tutorial mostra, passo a passo, como criar no Google Cloud Platform (GCP) todo o fluxo do **Vertex AI Vector Search**: preparar os dados (vetores), criar o **índice**, criar o **endpoint** e fazer o **deploy** do índice no endpoint para consultas. Ao final você terá um Vector Store consultável via API.

**Documentação de referência (Google Cloud):**
- [Vertex AI Vector Search – Visão geral](https://docs.cloud.google.com/vertex-ai/docs/vector-search/overview)
- [Antes de começar (setup)](https://docs.cloud.google.com/vertex-ai/docs/vector-search/setup)
- [Criar e gerenciar índices](https://docs.cloud.google.com/vertex-ai/docs/vector-search/create-manage-index)
- [Implantar e gerenciar endpoints públicos](https://docs.cloud.google.com/vertex-ai/docs/vector-search/deploy-index-public)
- [Formato dos dados de entrada](https://docs.cloud.google.com/vertex-ai/docs/vector-search/format-structure)
- [Atualizar e reconstruir um índice ativo](https://docs.cloud.google.com/vertex-ai/docs/vector-search/update-rebuild-index)
- [Quickstart (notebook)](https://docs.cloud.google.com/vertex-ai/docs/vector-search/quickstart)

**Console GCP:** [Vertex AI → Vector Search (índices e endpoints)](https://console.cloud.google.com/vertex-ai/matching-engine/indexes)

---

## O que você vai criar

1. **Bucket no Cloud Storage** — onde ficam os arquivos de vetores (JSONL).
2. **Índice (Index)** — estrutura que armazena os vetores para busca por similaridade (batch ou streaming).
3. **Endpoint de índice (Index Endpoint)** — “servidor” que recebe as consultas e usa o índice implantado.
4. **Deploy do índice no endpoint** — associa o índice ao endpoint e gera um **Deployed Index ID**, usado nas chamadas de busca.

Fluxo resumido: **dados no GCS → criar Índice → criar Endpoint → fazer Deploy do índice no Endpoint → consultar com `find_neighbors`**.

---

## Pré-requisitos

### 1. Projeto e billing

- Tenha um **projeto GCP** com **faturamento habilitado**.
- Anote o **ID do projeto** (ex.: `meu-projeto-123`). No Console: [Selecionar projeto](https://console.cloud.google.com/) ou use `gcloud config get-value project`.

### 2. APIs habilitadas

Habilite as APIs necessárias (Cloud Shell ou terminal com `gcloud` instalado):

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  compute.googleapis.com \
  --project=SEU_PROJECT_ID
```

Substitua `SEU_PROJECT_ID` pelo ID do seu projeto.

### 3. Permissões IAM

A conta que criará índices e endpoints precisa de, por exemplo:

- **Vertex AI User** (ou papel equivalente que permita criar índices e endpoints).
- **Storage Admin** (ou equivalente) no bucket que você usar para os vetores.

No Console: [IAM e administrador](https://console.cloud.google.com/iam-admin/iam) → adicione os papéis ao seu usuário ou à service account que for usar.

### 4. Escolher região

O Vertex AI Vector Search existe em [regiões específicas](https://cloud.google.com/vertex-ai/docs/general/locations). Exemplo comum: `us-central1`. Use a mesma região para bucket, índice e endpoint.

Defina uma variável para não repetir:

```bash
export LOCATION=us-central1
export PROJECT_ID=SEU_PROJECT_ID
```

---

## Passo 1: Decidir tipo de índice e de endpoint

### Tipo de índice

| Tipo            | Atualização      | Quando usar                          |
|-----------------|------------------|--------------------------------------|
| **Batch**       | Periódica (GCS)  | Atualizações em lote (diário/semanal) |
| **Streaming**   | Contínua         | Dados novos disponíveis em segundos   |

Para este tutorial, use **Batch**: você sobe um JSONL no GCS e cria (ou atualiza) o índice a partir dele.

### Tipo de endpoint

- **Público**: mais simples, acessível pela internet (com autenticação). Recomendado para começar.
- **VPC**: rede privada; exige configuração de VPC/Private Service Connect.

Seguiremos com **endpoint público**.

---

## Passo 2: Preparar os vetores (dados de entrada)

### Formato dos dados

Os vetores devem estar em **Cloud Storage**, em arquivos **JSONL** (uma linha JSON por registro). Cada linha pode ser:

- **Dense (recomendado para começar):** `id` + `embedding` (lista de floats).

Exemplo de conteúdo de um arquivo `data.jsonl`:

```json
{"id": "doc1", "embedding": [0.1, -0.2, 0.3, ...]}
{"id": "doc2", "embedding": [0.2, 0.1, -0.1, ...]}
```

- O número de dimensões do `embedding` deve ser **igual** ao parâmetro `dimensions` que você definir na criação do índice (ex.: 768 para `text-embedding-004`).
- O `id` deve ser único por registro.

Documentação completa: [Formato e estrutura dos dados de entrada](https://docs.cloud.google.com/vertex-ai/docs/vector-search/format-structure).

### Criar bucket e enviar o JSONL

1. Crie um bucket na mesma região do Vertex AI:

```bash
BUCKET_NAME="${PROJECT_ID}-vector-search-tutorial"
gsutil mb -l ${LOCATION} -p ${PROJECT_ID} gs://${BUCKET_NAME}
```

2. Crie um arquivo JSONL local com seus vetores (ex.: `vectors.jsonl`) e envie para uma pasta do bucket:

```bash
# Exemplo: criar um arquivo mínimo de teste (2 dimensões)
echo '{"id": "1", "embedding": [0.1, 0.2]}' > vectors.jsonl
echo '{"id": "2", "embedding": [0.3, 0.4]}' >> vectors.jsonl

gsutil cp vectors.jsonl gs://${BUCKET_NAME}/index_data/vectors.jsonl
```

O **URI do “diretório”** dos dados será: `gs://${BUCKET_NAME}/index_data/`. Esse URI será usado como `contentsDeltaUri` na criação do índice.

---

## Passo 3: Criar o índice (Vector Search Index)

O índice é o recurso que armazena os vetores e permite busca por similaridade. Você pode criar pelo **Console**, **gcloud** ou **Python SDK**.

### Opção A: Console (interface gráfica)

1. Abra o [Vector Search no Console](https://console.cloud.google.com/vertex-ai/matching-engine/indexes) (Vertex AI → Deploy and use → Vector Search).
2. Aba **Indexes** → **Create**.
3. Preencha:
   - **Display name**: ex. `meu-primeiro-indice`.
   - **Region**: mesma de `LOCATION`.
   - **Update method**: **Batch**.
   - **Shard size**: ex. **Small** (2 GiB) para poucos vetores; **Medium** (20 GiB) para volumes maiores.
   - **Dimensions**: número de dimensões do seu `embedding` (ex.: `2` no exemplo mínimo, ou `768` para embeddings de texto).
   - **Algorithm**: ex. **Tree AH**; em **Approximate neighbors count** use algo como `150`.
   - **Cloud Storage**: selecione a pasta onde está o JSONL (ex. `gs://SEU_BUCKET/index_data/`).
4. Clique em **Create**. A criação pode levar de alguns minutos a cerca de 1 hora, dependendo do tamanho dos dados.
5. Anote o **ID do índice** (aparece na lista após a criação).

### Opção B: gcloud (linha de comando)

1. Crie um arquivo de metadados do índice, por exemplo `index_metadata.json`:

```json
{
  "contentsDeltaUri": "gs://SEU_BUCKET_NAME/index_data/",
  "config": {
    "dimensions": 2,
    "approximateNeighborsCount": 150,
    "distanceMeasureType": "DOT_PRODUCT_DISTANCE",
    "algorithm_config": {
      "treeAhConfig": {
        "leafNodeEmbeddingCount": 500,
        "leafNodesToSearchPercent": 7
      }
    }
  }
}
```

Substitua:
- `SEU_BUCKET_NAME` pelo nome do bucket.
- O caminho em `contentsDeltaUri` pela pasta GCS que contém o(s) arquivo(s) JSONL.
- `dimensions` pelo número de dimensões dos seus vetores.

2. Crie o índice:

```bash
gcloud ai indexes create \
  --metadata-file=index_metadata.json \
  --display-name=meu-primeiro-indice \
  --region=${LOCATION} \
  --project=${PROJECT_ID}
```

3. Acompanhe a operação (o comando retorna um `OPERATION_ID`). Para ver o status:

```bash
gcloud ai operations describe OPERATION_ID --region=${LOCATION} --project=${PROJECT_ID}
```

4. Quando a operação estiver concluída, liste os índices e anote o **ID do índice**:

```bash
gcloud ai indexes list --region=${LOCATION} --project=${PROJECT_ID}
```

### Opção C: Python (Vertex AI SDK)

```python
from google.cloud import aiplatform

aiplatform.init(project=PROJECT_ID, location=LOCATION)

index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name="meu-primeiro-indice",
    contents_delta_uri=f"gs://{BUCKET_NAME}/index_data/",
    dimensions=2,  # use a dimensão dos seus embeddings
    approximate_neighbors_count=150,
    distance_measure_type="DOT_PRODUCT_DISTANCE",
)

# Aguardar conclusão (pode levar vários minutos)
print(index.resource_name)  # contém o ID do índice
```

O **Index ID** é o número longo no final do `resource_name` (ex.: `projects/123/locations/us-central1/indexes/4567890123456789012` → ID `4567890123456789012`).

---

## Passo 4: Criar o Index Endpoint

O **Index Endpoint** é o recurso que “serve” o índice: é nele que você implanta um ou mais índices e faz as consultas.

### Opção A: Console

1. No [Vector Search no Console](https://console.cloud.google.com/vertex-ai/matching-engine/indexes), abra a aba **Index endpoints**.
2. **Create** → **Create new index endpoint**.
3. Nome (ex. `meu-endpoint`), região igual à do índice, e **habilitar endpoint público** se for o caso.
4. Crie e anote o **ID do endpoint**.

### Opção B: gcloud

```bash
gcloud ai index-endpoints create \
  --display-name=meu-endpoint \
  --public-endpoint-enabled \
  --region=${LOCATION} \
  --project=${PROJECT_ID}
```

Anote o **INDEX_ENDPOINT_ID** retornado ou liste depois:

```bash
gcloud ai index-endpoints list --region=${LOCATION} --project=${PROJECT_ID}
```

### Opção C: Python

```python
from google.cloud import aiplatform

aiplatform.init(project=PROJECT_ID, location=LOCATION)

endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
    display_name="meu-endpoint",
    public_endpoint_enabled=True,
)
print(endpoint.resource_name)  # contém o ID do endpoint
```

---

## Passo 5: Fazer o deploy do índice no endpoint

Só após o **deploy** o índice fica consultável. Você associa o índice ao endpoint e define um **Deployed Index ID** (identificador único dessa implantação no endpoint).

### Pré-requisitos

- Índice no estado **Ready** (criação concluída).
- ID do **índice** e ID do **endpoint** em mãos.

### Opção A: Console

1. Em **Vector Search** → **Index endpoints**, abra o endpoint criado.
2. Use a opção para **Deploy index** (ou equivalente).
3. Selecione o índice e informe um **Deployed index ID** (ex.: `meu_indice_deployed` — apenas letras, números e underscores).
4. Confirme. O deploy pode levar até ~30 minutos na primeira vez.

### Opção B: gcloud

```bash
INDEX_ID="ID_DO_INDICE"
INDEX_ENDPOINT_ID="ID_DO_ENDPOINT"
DEPLOYED_INDEX_ID="meu_indice_deployed"

gcloud ai index-endpoints deploy-index ${INDEX_ENDPOINT_ID} \
  --deployed-index-id=${DEPLOYED_INDEX_ID} \
  --index=${INDEX_ID} \
  --region=${LOCATION} \
  --project=${PROJECT_ID}
```

Substitua `ID_DO_INDICE` e `ID_DO_ENDPOINT` pelos IDs reais.

### Opção C: Python

```python
from google.cloud import aiplatform

aiplatform.init(project=PROJECT_ID, location=LOCATION)

index = aiplatform.MatchingEngineIndex("INDEX_ID")  # ou resource_name completo
endpoint = aiplatform.MatchingEngineIndexEndpoint("INDEX_ENDPOINT_ID")

endpoint.deploy_index(
    index=index,
    deployed_index_id="meu_indice_deployed",
)
```

Após o deploy concluir, o endpoint passa a ter um “deployed index” ativo. Esse **deployed_index_id** é o que você usa nas consultas.

---

## Passo 6: Consultar o índice (find_neighbors)

Com o índice implantado no endpoint, você envia um vetor de consulta e recebe os vizinhos mais próximos.

### Exemplo em Python

```python
from google.cloud import aiplatform

aiplatform.init(project=PROJECT_ID, location=LOCATION)

endpoint = aiplatform.MatchingEngineIndexEndpoint("INDEX_ENDPOINT_ID")
query_vector = [0.15, 0.25]  # mesma dimensão do índice

response = endpoint.find_neighbors(
    deployed_index_id="meu_indice_deployed",
    queries=[query_vector],
    num_neighbors=5,
)

for neighbor in response[0]:
    print(f"id: {neighbor.id}, distance: {neighbor.distance}")
```

- `deployed_index_id`: o ID definido no deploy.
- `queries`: lista de vetores (cada vetor = uma consulta).
- `num_neighbors`: quantos vizinhos retornar por consulta.

Os atributos do vizinho podem variar conforme a versão do SDK (`id`/`datapoint_id`, `distance`); consulte a [documentação do MatchingEngineIndexEndpoint](https://cloud.google.com/python/docs/reference/aiplatform/latest/google.cloud.aiplatform.MatchingEngineIndexEndpoint).

---

## Resumo: variáveis para usar na aplicação

Depois de seguir os passos, você terá:

| Variável              | Onde obter |
|-----------------------|------------|
| `PROJECT_ID`          | Projeto GCP |
| `LOCATION`            | Região (ex.: `us-central1`) |
| `INDEX_ID`            | Lista de índices (Console ou gcloud) |
| `INDEX_ENDPOINT_ID`   | Lista de endpoints |
| `DEPLOYED_INDEX_ID`   | Nome que você deu no deploy |
| Bucket + pasta GCS    | Para novos batch updates (atualizações de índice) |

No projeto **agente-3-the-memory**, essas variáveis são usadas em `config/memory_policy.yaml` (seção `vector_search.vertex`) e/ou em variáveis de ambiente (`VECTOR_SEARCH_ENDPOINT_ID`, `VECTOR_SEARCH_INDEX_ID`, `VECTOR_SEARCH_GCS_BUCKET`, `VECTOR_SEARCH_DEPLOYED_INDEX_ID`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`).

---

## Atualizar um índice batch (novos vetores)

Para índices **batch**, você não recria o índice do zero a cada vez; você atualiza com um novo conjunto de dados no GCS:

1. Gere um novo JSONL com os vetores (incluindo os que já existem, se quiser manter).
2. Envie o arquivo para o bucket (ex.: outra pasta ou versão).
3. Chame a API de **update** do índice definindo `metadata.contentsDeltaUri` como o URI da nova pasta no GCS e, se for substituição total, `isCompleteOverwrite: true`.

Detalhes: [Atualizar e reconstruir um índice ativo](https://docs.cloud.google.com/vertex-ai/docs/vector-search/update-rebuild-index). No código do projeto, isso é feito em `src/indexing/vector_store.py` (fluxo Vertex).

---

## Limpeza (evitar custos)

Para não deixar recursos ativos:

1. **Undeploy** do índice no endpoint (Console ou `undeploy_index` / equivalente no gcloud).
2. **Excluir** o endpoint e o índice (Console ou comandos `delete`).
3. **Excluir** os objetos do bucket ou o bucket inteiro.

Exemplo em Python (após undeploy):

```python
endpoint.undeploy_all()
endpoint.delete(force=True)
index.delete()
```

---

## Checklist final

- [ ] Projeto GCP com billing e APIs habilitadas.
- [ ] Bucket criado; JSONL de vetores enviado; URI anotado.
- [ ] Índice criado (Batch) com `dimensions` igual ao do embedding.
- [ ] Index Endpoint criado (público).
- [ ] Deploy do índice no endpoint com um `deployed_index_id`.
- [ ] Teste de consulta com `find_neighbors` funcionando.
- [ ] Variáveis (ou config) preenchidas na aplicação que usa Vector Search.

Se todos os itens estiverem ok, você tem o Vector Store (índice + endpoint) pronto para uso no GCP.

---

## Validação: o que pode estar faltando

Antes de usar o tutorial em produção, confira:

| Ponto | Descrição |
|-------|-----------|
| **Índice em estado Ready** | A criação do índice é assíncrona. No Console, verifique o status na lista de índices; via gcloud, use `gcloud ai operations describe` até `done: true`. Só faça o deploy quando o índice estiver **Ready**. |
| **ID da operação** | Ao criar índice ou endpoint, o comando retorna um `OPERATION_ID`. O **ID do recurso** (índice ou endpoint) aparece na operação concluída ou na listagem (`gcloud ai indexes list` / `gcloud ai index-endpoints list`). |
| **Dimensões do embedding** | O valor de `dimensions` na criação do índice deve ser **exatamente** o mesmo do seu modelo de embedding (ex.: 768 para `text-multilingual-embedding-002`). Se não bater, a criação ou a consulta pode falhar. |
| **Custos** | Vector Search é serviço pago (índice + endpoint + consultas). Consulte [Preços do Vertex AI](https://cloud.google.com/vertex-ai/pricing#vectorsearch). Faça limpeza após testes. |
| **Quota e regiões** | Algumas regiões podem ter quota limitada. Se a criação falhar, tente outra região ou solicite aumento de quota. |
| **Autenticação** | Para usar a API (Python ou gcloud), é necessário estar autenticado: `gcloud auth application-default login` ou use uma service account com os papéis corretos. |

---

## Glossário

Definições dos termos e conceitos usados no tutorial, em ordem alfabética.

---

### Termos do Vertex AI Vector Search

**Vertex AI Vector Search**  
Serviço do Google Cloud (Vertex AI) que permite buscar itens “mais parecidos” com um vetor de consulta. Funciona como um banco de vetores (vector store): você indexa vetores (embeddings) e depois consulta por similaridade. Antes era chamado de Matching Engine.

**Vector Index (Índice de vetores / Matching Engine Index)**  
Recurso no GCP que armazena os vetores e a estrutura de busca (ex.: árvore Tree AH). O índice em si **não** recebe requisições HTTP; ele precisa ser **implantado** em um Index Endpoint para ser consultado. Pode ser atualizado em **batch** (dados no GCS) ou em **streaming**.

**Index Endpoint (Endpoint de índice)**  
Recurso que “serve” um ou mais índices. É o ponto de acesso para consultas: sua aplicação chama o endpoint (com autenticação) e informa qual **Deployed Index ID** usar. Pode ser **público** (acessível pela internet) ou **privado** (VPC).

**Deployed Index / Deployed Index ID**  
Quando você faz o **deploy** de um índice em um endpoint, essa implantação recebe um identificador definido por você: o **Deployed Index ID**. É esse ID que você passa em `find_neighbors(deployed_index_id=...)` para indicar qual índice consultar (um endpoint pode ter vários índices implantados).

**contentsDeltaUri**  
URI no Cloud Storage (ex.: `gs://bucket/pasta/`) onde estão os arquivos de vetores (JSONL ou CSV) usados para **criar** ou **atualizar** um índice batch. O Vertex lê os arquivos nessa pasta para (re)construir o índice.

**Batch (índice batch)**  
Tipo de índice cuja atualização é feita em lote: você coloca os vetores em um bucket GCS e dispara uma operação de criação ou update. Leva minutos a horas para refletir. Indicado para atualizações periódicas (diária, semanal).

**Streaming (índice streaming)**  
Tipo de índice que aceita atualizações contínuas (upsert por registro). As mudanças ficam disponíveis para busca em segundos. Exige configuração diferente do batch (incluindo `index_update_method=STREAM_UPDATE`).

**find_neighbors**  
Método da API que recebe um ou mais vetores de consulta e retorna os vizinhos mais próximos no índice (por distância ou similaridade). Parâmetros típicos: `deployed_index_id`, `queries` (lista de vetores), `num_neighbors`. Retorno: por exemplo, lista de listas de vizinhos, cada um com `id` (ou `datapoint_id`) e `distance`.

**Embedding**  
Representação numérica (vetor de números) de um dado (texto, imagem, etc.). No contexto do tutorial, é a lista de floats em cada linha do JSONL (`"embedding": [0.1, -0.2, ...]`). O número de elementos do vetor é a **dimensão** (dimensions).

**Dimensions (dimensões)**  
Número de componentes do vetor de embedding (ex.: 768). Deve ser o mesmo na criação do índice e nos dados (JSONL); caso contrário a indexação ou a consulta falha.

**DOT_PRODUCT_DISTANCE**  
Tipo de “distância” usada para comparar vetores no índice. Produto interno (dot product); em muitos casos vetores são normalizados e então equivale a similaridade de cosseno. Deve ser consistente com o modelo de embedding usado.

**COSINE_DISTANCE**  
Outra medida suportada: distância baseada no cosseno do ângulo entre vetores. Escolha conforme o que seu modelo de embedding otimiza.

**Tree AH (Approximate Nearest Neighbors)**  
Algoritmo de busca aproximada usado pelo Vertex. Parâmetros como `leafNodeEmbeddingCount` e `leafNodesToSearchPercent` (ou `fractionLeafNodesToSearch`) controlam a precisão e o custo da busca.

**approximateNeighborsCount (approximate_neighbors_count)**  
Quantidade típica de vizinhos que você pretende recuperar por consulta. Usado na construção do índice para otimizar a estrutura (ex.: Tree AH).

**Shard size**  
Tamanho de cada “fatia” do índice (ex.: SMALL 2 GiB, MEDIUM 20 GiB, LARGE 50 GiB). Afeta desempenho e tipo de máquina no deploy. Para poucos vetores, SMALL costuma bastar.

---

### Termos de infra e dados

**GCS (Google Cloud Storage)**  
Serviço de armazenamento de objetos do GCP. Os arquivos JSONL de vetores precisam estar em um **bucket** GCS; o URI do bucket/pasta é o `contentsDeltaUri`.

**JSONL (JSON Lines)**  
Formato de arquivo em que cada linha é um objeto JSON independente. No tutorial, cada linha tem `id` e `embedding` (e opcionalmente outros campos). É o formato recomendado para entrada de vetores no Vertex.

**Bucket**  
Container no GCS onde você armazena arquivos. O nome do bucket é globalmente único no GCP. Ex.: `gs://meu-bucket/index_data/vectors.jsonl`.

---

### Ferramentas e SDK

**gcloud**  
CLI do Google Cloud. Comandos como `gcloud ai indexes create`, `gcloud ai index-endpoints create` e `gcloud ai index-endpoints deploy-index` criam e gerenciam índices e endpoints.

**Vertex AI SDK for Python (aiplatform)**  
Biblioteca Python para Vertex AI. No tutorial, `aiplatform.MatchingEngineIndex` e `aiplatform.MatchingEngineIndexEndpoint` são usados para criar índice, endpoint, deploy e chamar `find_neighbors`.

**Matching Engine**  
Nome antigo do serviço hoje chamado Vertex AI Vector Search. Ainda aparece em nomes de classes do SDK (ex.: `MatchingEngineIndex`, `MatchingEngineIndexEndpoint`).

---

### Significado dos blocos de código do tutorial

| Bloco | O que faz |
|-------|-----------|
| **APIs (Pré-requisitos)** | Habilita no projeto as APIs do Vertex AI, Cloud Storage e Compute Engine, necessárias para criar índice, endpoint e rodar o serviço. |
| **export LOCATION / PROJECT_ID** | Define variáveis de ambiente para região e projeto, usadas nos comandos seguintes (evita repetir valores). |
| **gsutil mb** | Cria um bucket no GCS na região e no projeto indicados. |
| **echo + gsutil cp (Passo 2)** | Cria um arquivo JSONL mínimo com dois vetores de exemplo (2 dimensões) e envia para uma pasta do bucket; o URI da pasta é o `contentsDeltaUri`. |
| **index_metadata.json (gcloud)** | Arquivo de configuração do índice: URI dos dados no GCS, dimensão, tipo de distância e parâmetros do algoritmo Tree AH. |
| **gcloud ai indexes create** | Dispara a criação assíncrona do índice no Vertex; o comando retorna um ID de operação, não o ID do índice (este sai na listagem após a operação terminar). |
| **gcloud ai operations describe** | Consulta o status de uma operação assíncrona (ex.: criação de índice) até aparecer concluída. |
| **gcloud ai index-endpoints create** | Cria um endpoint de índice público na região; após concluído, você obtém o INDEX_ENDPOINT_ID. |
| **gcloud ai index-endpoints deploy-index** | Associa um índice já existente a um endpoint e define o Deployed Index ID; a partir daí o índice fica consultável nesse endpoint. |
| **MatchingEngineIndex.create_tree_ah_index (Python)** | Cria um índice batch via SDK: nome, URI do GCS, dimensão, quantidade aproximada de vizinhos e tipo de distância. |
| **MatchingEngineIndexEndpoint.create (Python)** | Cria um endpoint de índice com endpoint público habilitado. |
| **endpoint.deploy_index (Python)** | Faz o deploy de um objeto `MatchingEngineIndex` em um `MatchingEngineIndexEndpoint` com um `deployed_index_id` escolhido por você. |
| **endpoint.find_neighbors (Python)** | Envia um ou mais vetores de consulta ao índice implantado e recebe, para cada consulta, uma lista de vizinhos com `id` e `distance`. |
| **endpoint.undeploy_all() / delete (Limpeza)** | Remove todas as implantações do endpoint e depois exclui o endpoint e o índice para evitar custos. |
