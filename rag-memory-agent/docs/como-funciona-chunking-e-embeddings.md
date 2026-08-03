# Como este projeto funciona: Chunking e Embeddings (da ingestão à consulta)

> **Objetivo deste documento:** explicar, arquivo por arquivo, como um documento bruto (PDF, CSV, TXT, JSON) vira "memória de longo prazo" pesquisável — e como uma pergunta em linguagem natural encontra os trechos certos. Sem pressa, com ilustrações.

---

## O mapa geral (visão de 10.000 metros)

Antes de mergulhar nos arquivos, veja o caminho completo que um documento percorre:

```
  INGESTÃO (escrita na memória)
  ─────────────────────────────

  📄 PDF/CSV/TXT/JSON          🔪 Chunking              🧮 Embedding            🗄️ Vector Store
  ┌──────────────────┐    ┌────────────────────┐   ┌───────────────────┐   ┌──────────────────┐
  │ "A conta premium │    │ ["A conta premium  │   │ [0.12, -0.98, ...]│   │  ChromaDB        │
  │  é isenta de     │───▶│   é isenta..."],   │──▶│ [0.45,  0.33, ...]│──▶│  (data/chroma)   │
  │  taxa. TED é..." │    │  ["TED é..."]      │   │  (vetores de 384  │   │  id + vetor +    │
  └──────────────────┘    └────────────────────┘   │   números)        │   │  texto original  │
   loaders.py              chunking.py             └───────────────────┘   └──────────────────┘
                                                    embedding.py            vector_store.py


  CONSULTA (leitura da memória)
  ─────────────────────────────

  ❓ "Qual a tarifa       🧮 Embedding da         🔍 Busca por           📋 Trechos mais
      da conta premium?"     pergunta                similaridade            parecidos
  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
  │  pergunta do     │──▶│ [0.11, -0.95,...]│──▶│ compara o vetor  │──▶│ "Conta premium   │
  │  usuário         │   │ (mesmo modelo!)  │   │ da pergunta com  │   │  isenta de taxa  │
  └──────────────────┘   └──────────────────┘   │ todos os vetores │   │  de manutenção…" │
   rag_query.py           embedding.py          └──────────────────┘   └──────────────────┘
                                                 memory_gateway.py
```

**A grande sacada do RAG:** texto não é comparável diretamente por computador ("tarifa" e "taxa" são palavras diferentes, mas significam quase a mesma coisa). Então convertemos **tudo** — documentos e perguntas — para **vetores numéricos** que capturam o *significado*. Aí sim dá para comparar matematicamente.

---

## Parte 0 — Os dados de entrada (`data/lab/`)

O laboratório usa três documentos de um banco fictício:

| Arquivo | Formato | Conteúdo |
|---|---|---|
| `data/lab/lab_conta_premium.pdf` | PDF | Regras e benefícios da conta premium |
| `data/lab/lab_tarifas.csv` | CSV | Tabela de tarifas (manutenção, TED, saque…) |
| `data/lab/lab_emprestimo.txt` | TXT | Condições de empréstimo pessoal |

São formatos diferentes de propósito: o pipeline precisa saber **ler cada um** e normalizar tudo para o mesmo formato interno. É aí que entram os *loaders*.

---

## Parte 1 — Loaders: lendo qualquer formato (`src/indexing/loaders.py`)

**O problema:** um PDF tem páginas, um CSV tem colunas, um TXT é só texto. Precisamos de um "tradutor universal" que transforme qualquer entrada em uma lista padronizada de documentos.

**A solução:** uma função única que olha a extensão do arquivo e delega para o leitor certo:

```30:39:src/indexing/loaders.py
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path, text_column=csv_text_column)
    if suffix == ".json":
        return _load_json(path, text_path=json_text_path)
    if suffix == ".pdf":
        return _load_pdf(path, merge_pages=pdf_merge_pages)
    if suffix == ".txt":
        return _load_txt(path)
    raise ValueError(f"Formato não suportado: {suffix}. Use .csv, .json, .pdf ou .txt.")
```

Não importa a origem, a saída é **sempre** a mesma estrutura:

```python
[
  {"text": "texto do documento...", "metadata": {"source": "lab_tarifas.csv", "tipo": "ted"}},
  {"text": "outro documento...",    "metadata": {"source": "lab_tarifas.csv", "tipo": "saque"}},
]
```

Dois detalhes didáticos importantes:

**1. No CSV, cada linha vira um documento.** O texto sai da coluna `content` e as demais colunas viram *metadados* (úteis depois para filtrar buscas):

```42:54:src/indexing/loaders.py
def _load_csv(path: Path, text_column: str = "content") -> list[dict]:
    docs = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get(text_column) or row.get("text", "")
            if not (text and str(text).strip()):
                continue
            metadata = {"source": path.name}
            for k, v in row.items():
                if k != text_column and k != "text" and v:
                    metadata[k] = v
            docs.append({"text": str(text).strip(), "metadata": metadata})
    return docs
```

**2. No PDF, extraímos o texto de cada página** (via `pypdf`) e, por padrão, juntamos tudo em um documento só (`merge_pages: true` no `config/indexing.yaml`). Isso evita que uma frase cortada no fim da página vire dois pedaços sem sentido:

```120:122:src/indexing/loaders.py
    if merge_pages:
        full = "\n\n".join(t for _, t in pages)
        return [{"text": full, "metadata": {"source": path.name, "pages": len(pages)}}]
```

> **Por que metadados importam?** Quando o chunk chega ao banco vetorial, ele carrega `source`, `tipo`, `page`... Isso permite responder "de onde veio essa informação?" e filtrar buscas (ex.: só documentos de tarifas).

---

## Parte 2 — Chunking: cortando o texto em pedaços (`src/indexing/chunking.py`)

### Por que cortar?

Dois motivos:

1. **Modelos de embedding têm limite de entrada.** Não dá para transformar um PDF de 50 páginas em um único vetor — e, mesmo que desse, o vetor viraria uma "média" borrada de todos os assuntos.
2. **Precisão na recuperação.** Se a pergunta é "qual a tarifa de TED?", queremos devolver o *parágrafo* sobre TED, não o documento inteiro.

Pense em um livro: você não decora o livro inteiro como um bloco. Você lembra por **trechos** — e é o trecho certo que você "recupera" quando alguém pergunta algo.

### O dilema do tamanho

```
  Chunk MUITO PEQUENO (ex.: 50 chars)          Chunk MUITO GRANDE (ex.: 5000 chars)
  ┌─────────────────────┐                      ┌────────────────────────────────────┐
  │ "isento até 5 por"  │  ← perdeu o          │ tarifas + empréstimo + cartão +    │
  └─────────────────────┘    contexto!         │ investimentos, tudo junto          │
   Quem é isento? De quê?                      └────────────────────────────────────┘
                                                ← o vetor vira uma "sopa" de temas;
                                                  a busca fica imprecisa
```

O ponto de equilíbrio usado neste projeto (definido em `config/indexing.yaml`): **512 caracteres com overlap de 64**.

### A função central

```18:48:src/indexing/chunking.py
def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int = 0,
    strategy: str = "fixed",
) -> list[str]:
    """
    Divide texto em pedaços.

    Args:
        text: texto a segmentar.
        chunk_size: tamanho máximo do chunk (caracteres, ou tokens se strategy=by_tokens).
        overlap: sobreposição entre chunks (chars em fixed; tokens em by_tokens).
        strategy: "fixed" | "by_paragraph" | "by_sentence" | "recursive" | "by_tokens".

    Returns:
        Lista de strings (chunks).
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if strategy == "by_paragraph":
        return _chunk_by_paragraph(text, chunk_size)
    if strategy == "by_sentence":
        return _chunk_by_sentence(text, chunk_size)
    if strategy == "by_tokens":
        return _chunk_by_tokens(text, chunk_size, overlap)
    if strategy == "recursive":
        return _chunk_recursive(text, chunk_size)
    return _chunk_fixed(text, chunk_size, overlap)
```

### As 5 estratégias, uma a uma

#### 1. `fixed` — a tesoura cega

Corta a cada N caracteres, sem olhar o conteúdo. Simples, mas pode cortar **no meio de uma palavra ou frase**:

```76:86:src/indexing/chunking.py
def _chunk_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    overlap = min(max(0, overlap), chunk_size - 1)
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if overlap else end
    return chunks
```

**O que é *overlap* (sobreposição)?** Cada chunk repete o finalzinho do anterior, como telhas de um telhado. Se uma informação cair exatamente na fronteira do corte, ela sobrevive inteira em pelo menos um dos chunks:

```
  Texto:    A B C D E F G H I J K L M N O P
                                              chunk_size=8, overlap=3

  Chunk 1:  [A B C D E F G H]
  Chunk 2:            [F G H I J K L M]       ← repete F G H
  Chunk 3:                      [K L M N O P] ← repete K L M
                       ╰──╯
                      overlap: a "emenda" fica coberta duas vezes
```

#### 2. `by_sentence` — respeita frases

Quebra o texto nas pontuações (`.`, `!`, `?`) e vai **acumulando frases inteiras** até encher o `chunk_size`:

```89:106:src/indexing/chunking.py
def _chunk_by_sentence(text: str, chunk_size: int) -> list[str]:
    # Quebra em sentenças: após . ! ? seguido de espaço ou fim
    raw = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in raw if s.strip()]
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s_len = len(s) + 1  # +1 pelo espaço entre sentenças
        if current_len + s_len > chunk_size and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(s)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return chunks
```

Nenhum chunk termina no meio de uma frase — mas frases muito longas podem estourar o limite.

#### 3. `by_paragraph` — respeita parágrafos

Mesma lógica, mas a unidade é o parágrafo (separado por linha em branco, `\n\n`). Ótimo para documentos bem estruturados; ruim para textos "corridos" sem parágrafos.

#### 4. `recursive` — a estratégia inteligente (e a usada no projeto)

Tenta preservar a **maior estrutura possível** e só desce de nível quando não cabe:

```
  1º) tenta quebrar por PARÁGRAFO  (\n\n)     ─┐
  2º) parágrafo grande? quebra por LINHA (\n)  │ desce um nível
  3º) linha grande? quebra por SENTENÇA (.!?)  │ apenas quando
  4º) sentença grande? quebra por PALAVRA ( )  │ necessário
  5º) ainda grande? corte fixo                ─┘
```

```134:147:src/indexing/chunking.py
def _chunk_recursive(text: str, chunk_size: int, separators: list | None = None) -> list[str]:
    """
    Recursive: tenta quebrar por parágrafo -> linha -> sentença -> palavra;
    pedaços maiores que chunk_size são quebrados no próximo nível.
    """
    if separators is None:
        separators = _RECURSIVE_SEPARATORS
    if len(text) <= chunk_size:
        return [text] if text else []
    if not separators:
        return _chunk_fixed(text, chunk_size, 0)
    sep = separators[0]
    rest_seps = separators[1:]
    parts = _split_by_sep(text, sep)
```

É a mesma ideia do `RecursiveCharacterTextSplitter` do LangChain — o padrão de mercado.

#### 5. `by_tokens` — conta como o modelo conta

**O que é um token?** Modelos de linguagem não leem letra por letra nem palavra por palavra: leem *tokens* — pedaços de palavra. "Empréstimo" pode virar 3 tokens (`Emp`, `rést`, `imo`). Como os limites dos modelos são em tokens (não em caracteres), essa estratégia corta contando tokens de verdade, usando a biblioteca `tiktoken`:

```51:73:src/indexing/chunking.py
def _chunk_by_tokens(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """
    Chunk por tokens (tiktoken encoding cl100k_base).
    chunk_size e overlap são contados em tokens, não em caracteres.
    """
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if not tokens:
        return []
    overlap = min(max(0, overlap), max(0, chunk_size - 1))
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        piece = enc.decode(tokens[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= len(tokens):
            break
        start = end - overlap if overlap else end
    return chunks
```

### Como comparar estratégias na prática

O script `scripts/chunk_inspect.py` (Lab 1) roda todas as estratégias sobre os documentos de `data/lab/` e imprime estatísticas — incluindo a métrica `mid_sentence%` (percentual de chunks que terminam no meio de uma frase, ou seja, cortes "feios"):

```bash
python scripts/chunk_inspect.py --compare
python scripts/chunk_inspect.py --strategy fixed --size 128 --show-chunks
```

```35:40:scripts/chunk_inspect.py
def _ends_mid_sentence(chunk: str) -> bool:
    """Heurística: chunk não termina em pontuação de fim de frase."""
    c = chunk.rstrip()
    if not c:
        return False
    return c[-1] not in ".!?;:"
```

---

## Parte 3 — Embeddings: transformando texto em números (`src/indexing/embedding.py`)

### A ideia em uma frase

Um **embedding** é uma lista de números (um *vetor*) que representa o **significado** de um texto. Textos de significado parecido viram vetores "próximos"; textos de significados diferentes viram vetores "distantes".

```
                       "tarifa de manutenção" ──▶ [0.82, 0.11, -0.30, ...]
  Espaço vetorial       "taxa mensal da conta" ─▶ [0.79, 0.15, -0.28, ...]  ← quase igual!
  (aqui em 2D, no       "receita de bolo" ──────▶ [-0.55, 0.90, 0.12, ...] ← longe
  projeto são 384
  dimensões)                        ▲
                                    │      • taxa mensal
                                    │    • tarifa de manutenção
                                    │
                                    │                      • receita de bolo
                                    └──────────────────────────▶
```

O modelo usado (`paraphrase-multilingual-MiniLM-L12-v2`) gera vetores de **384 dimensões**. Não conseguimos visualizar 384 eixos, mas a matemática funciona igual à do plano 2D acima.

> **Analogia:** pense no embedding como as coordenadas GPS de um significado. "Tarifa" e "taxa" moram no mesmo bairro; "receita de bolo" mora em outra cidade. A busca vetorial é perguntar: *"quais moradores estão mais perto deste endereço?"*

### Três backends, um contrato

A função `embed_texts` aceita uma lista de textos e devolve uma lista de vetores, escolhendo o motor pelo `config/indexing.yaml`:

| Backend | O que é | Quando usar |
|---|---|---|
| `local` | `sentence-transformers` rodando na sua máquina (384 dims) | Labs, offline, sem custo |
| `vertex` | API do Google Vertex AI (`text-multilingual-embedding-002`, 768 dims) | Produção |
| `mock` | Hash determinístico do texto (sem semântica real!) | Testes/CI |

```20:29:config/indexing.yaml
embedding:
  # Backend: local | vertex | mock
  # local = sentence-transformers (offline, semântico; requer pip install -e ".[lab]")
  # vertex = Vertex AI (requer GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION)
  # mock = hash determinístico (só para CI/smoke; semântica limitada)
  # IMPORTANTE: trocar de backend exige apagar data/chroma e reindexar (dimensões diferentes).
  backend: local
  # Modelo local (384 dims) ou Vertex (text-multilingual-embedding-002 = 768 dims)
  model: paraphrase-multilingual-MiniLM-L12-v2
  batch_size: 5
```

O backend local, na prática, é só isso — carregar o modelo uma vez (cache) e codificar:

```136:151:src/indexing/embedding.py
def _embed_local(texts: list[str], *, model: str, for_query: bool = False) -> list[list[float]]:
    """Embeddings locais via sentence-transformers (offline após download do modelo)."""
    from sentence_transformers import SentenceTransformer

    if model not in _local_model_cache:
        logger.info("Carregando modelo local de embedding: %s (primeiro uso pode baixar ~470MB)", model)
        _local_model_cache[model] = SentenceTransformer(model)
    encoder: SentenceTransformer = _local_model_cache[model]  # type: ignore[assignment]
    # sentence-transformers trata query/doc de forma similar para MiniLM; normalize para cosine
    vectors = encoder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [v.tolist() for v in vectors]
```

Repare no `normalize_embeddings=True` — vamos entender o porquê já já, na similaridade de cosseno.

### Similaridade de cosseno — o coração da busca (ilustrado)

Como medir se dois vetores são "parecidos"? Medindo o **ângulo** entre eles. A similaridade de cosseno é o cosseno desse ângulo:

```
  Vetores APONTANDO NA MESMA DIREÇÃO           Vetores em DIREÇÕES DIFERENTES
  (significados parecidos)                     (significados sem relação)

        ▲                                            ▲
        │     B ("taxa mensal")                      │  B ("receita de bolo")
        │    ↗                                       │ ↑
        │   ↗ ← ângulo θ pequeno                     │ │   ← ângulo θ ≈ 90°
        │  ↗↗                                        │ │
        │ ↗ A ("tarifa de manutenção")               │ └────↗ A ("tarifa")
        └──────────────▶                             └──────────────▶

  cos(θ) ≈ 1.0  →  MUITO similares               cos(θ) ≈ 0.0  →  nada a ver
```

Escala de leitura:

```
  cos(θ) =  1.0   mesmíssimo significado (vetores paralelos)
  cos(θ) =  0.7   bem relacionados
  cos(θ) =  0.35  relação fraca  ← limiar mínimo usado neste projeto
  cos(θ) =  0.0   sem relação (vetores perpendiculares)
```

A fórmula é: produto escalar dividido pelos comprimentos dos vetores. O projeto tem a implementação didática, dá para ler linha a linha:

```199:208:src/indexing/embedding.py
def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade cosseno entre dois vetores (utilitário para labs/testes)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
```

**Exemplo numérico com vetores de brinquedo (2D):**

```
  A = [3, 4]           B = [6, 8]           C = [4, -3]

  A vs B:  dot = 3·6 + 4·8 = 50
           |A| = √(9+16) = 5      |B| = √(36+64) = 10
           cos = 50 / (5 · 10) = 1.0   ← mesma direção! (B é só A "esticado")

  A vs C:  dot = 3·4 + 4·(-3) = 0
           cos = 0 / (5 · 5) = 0.0     ← perpendiculares, nada a ver
```

**Por que cosseno e não distância "de régua" (euclidiana)?** Porque o cosseno ignora o *tamanho* do vetor e olha só para a *direção* — e a direção é onde mora o significado. Um texto longo e um curto sobre o mesmo assunto apontam para o mesmo lado. (E é por isso que o código normaliza os vetores para comprimento 1: com vetores normalizados, cosseno e distância viram equivalentes e a busca fica mais rápida.)

---

## Parte 4 — Vector Store: guardando os vetores (`src/indexing/vector_store.py`)

Com os chunks vetorizados, precisamos de um banco que saiba responder: *"dado este vetor de pergunta, quais são os N vetores mais próximos?"*. É o **banco vetorial**. O projeto suporta três (mesmo padrão dos embeddings):

- **`chroma`** (o usado nos labs) — ChromaDB persistido em disco, em `data/chroma/`
- **`vertex`** — Vertex AI Vector Search (produção, GCP)
- **`mock`** — um arquivo JSONL simples (testes)

A escolha vem do `config/memory_policy.yaml`:

```11:23:config/memory_policy.yaml
vector_search:
  # Backend: chroma | vertex | mock (indexação e busca usam o mesmo)
  backend: chroma
  # Limite máximo de documentos retornados na busca
  max_documents: 3
  # Score mínimo de similaridade (cosine: max(0, 1 - distance) no Chroma).
  # Com embeddings locais (MiniLM), 0.35–0.55 costuma ser um bom intervalo;
  # com Vertex multilingual-002, valores mais altos (0.6–0.8) são comuns.
  min_similarity_score: 0.35
  # ChromaDB (quando backend: chroma)
  chroma:
    persist_directory: data/chroma
    collection_name: customer_insights
```

O ponto mais importante do arquivo: ao criar a coleção do Chroma, dizemos explicitamente que a **métrica de distância é cosseno**:

```27:36:src/indexing/vector_store.py
def _get_chroma_collection(persist_directory: str, collection_name: str):
    import numpy as np
    if not hasattr(np, "float_"):
        np.float_ = np.float64
    if not hasattr(np, "int_"):
        np.int_ = np.int64
    import chromadb

    client = chromadb.PersistentClient(path=persist_directory)
    return client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
```

> **O que é esse `hnsw`?** É o algoritmo de índice (*Hierarchical Navigable Small World*). Comparar a pergunta com **todos** os vetores um a um ficaria lento com milhões de documentos. O HNSW monta uma espécie de "malha de atalhos" entre vetores vizinhos, permitindo achar os mais próximos sem visitar todo mundo — como usar um GPS com rodovias em vez de testar cada rua da cidade.

E a gravação em si (`upsert`) manda tudo junto — id, vetor, texto original e metadados:

```58:77:src/indexing/vector_store.py
    if backend == "chroma":
        chroma_cfg = vs_cfg.get("chroma") or {}
        persist_dir = chroma_cfg.get("persist_directory", "data/chroma")
        collection_name = chroma_cfg.get("collection_name", "customer_insights")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        collection = _get_chroma_collection(persist_dir, collection_name)
        documents = [m.get("content", "") for m in metadatas]
        meta_serializable = []
        for m in metadatas:
            row = {}
            for k, v in m.items():
                if k is None or not isinstance(k, str):
                    continue
                if v is None or isinstance(v, (str, int, float, bool)):
                    row[k] = v
                else:
                    row[k] = str(v)
            meta_serializable.append(row)
        collection.add(ids=ids, embeddings=vectors, documents=documents, metadatas=meta_serializable)
        logger.info("Vector store ChromaDB: %d documentos gravados em %s", len(ids), persist_dir)
        return
```

> **Por que guardar o texto original junto do vetor?** Porque o vetor é irrecuperável de volta para texto. Na hora da consulta, a busca acha os *vetores* mais próximos, mas quem vai para o prompt do LLM é o *texto* que gravamos junto.

---

## Parte 5 — A ingestão de ponta a ponta (`src/indexing/__main__.py`)

Este é o **maestro** que rege as partes 1 a 4. É um CLI:

```bash
# Só gerar os chunks e inspecionar (sem gravar no banco)
python -m src.indexing --input data/lab/lab_conta_premium.pdf data/lab/lab_tarifas.csv data/lab/lab_emprestimo.txt --output out/chunks_lab.json

# Pipeline completo: chunking + embedding + gravação no ChromaDB
python -m src.indexing --input data/lab/ --push
```

O laço principal mostra o pipeline com clareza — carrega, chunka e anota cada pedaço com `source`, `chunk_index` e `chunk_id`:

```60:83:src/indexing/__main__.py
    for inp in input_paths:
        if not inp.exists():
            logger.warning("Arquivo não encontrado: %s", inp)
            continue
        docs = load_documents_from_file(
            inp,
            csv_text_column=csv_col,
            json_text_path=json_path,
            pdf_merge_pages=pdf_merge,
        )
        for doc in docs:
            text = doc["text"]
            meta_base = dict(doc["metadata"])
            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap, strategy=strategy)
            for i, c in enumerate(chunks):
                rec = {
                    "content": c,
                    "source": meta_base.get("source", inp.name),
                    "chunk_index": i,
                    "metadata": {k: v for k, v in meta_base.items() if k != "source"},
                }
                rec["metadata"]["chunk_id"] = str(chunk_id)
                all_chunks.append(rec)
                chunk_id += 1
```

E o `--push` fecha o ciclo: vetoriza tudo e grava no vector store:

```95:114:src/indexing/__main__.py
    if push:
        texts = [c["content"] for c in all_chunks]
        vectors = embed_texts(
            texts,
            model=emb_cfg.get("model"),
            batch_size=int(emb_cfg.get("batch_size", 5)),
            backend=emb_cfg.get("backend"),
            config_path=config_path,
        )
        ids = [c["metadata"].get("chunk_id", str(i)) for i, c in enumerate(all_chunks)]
        metadatas = [{**c["metadata"], "content": c["content"], "source": c["source"]} for c in all_chunks]
        upsert_documents(
            ids,
            vectors,
            metadatas,
            config_path=Path("config/memory_policy.yaml"),
            use_mock_if_unconfigured=vs_cfg.get("use_mock_if_unconfigured", True),
            mock_output_path=os.environ.get("INDEXING_MOCK_OUTPUT"),
        )
        logger.info("Push concluído: %d documentos.", len(ids))
```

Um chunk gravado fica assim (exemplo real de `out/chunks_lab.json`):

```json
{
  "content": "Conta premium isenta de taxa de manutenção mensal. Demais contas: R$ 25",
  "source": "lab_tarifas.csv",
  "chunk_index": 0,
  "metadata": { "tipo": "manutencao", "valor": "0", "chunk_id": "0" }
}
```

---

## Parte 6 — A consulta: perguntando à memória (`src/memory_gateway.py`)

A classe `LongTermMemoryGateway` é a "porta de entrada" da memória de longo prazo. Quem quer contexto chama um único método: `search_customer_insights(query)`.

O fluxo interno, para o backend Chroma:

```
  1. pergunta ──▶ embed_texts([query], for_query=True)   ← MESMO modelo da ingestão!
  2. vetor da pergunta ──▶ chroma.query(n_results=3)     ← 3 vizinhos mais próximos
  3. Chroma devolve DISTÂNCIAS ──▶ similaridade = 1 - distância
  4. filtra quem tem similaridade < 0.35 (min_similarity_score)
  5. ordena do mais similar ao menos e junta os textos
```

O trecho central:

```140:178:src/memory_gateway.py
                from src.indexing.embedding import embed_texts
                query_embeddings = embed_texts([query], for_query=True)
                if not query_embeddings:
                    return ""
                kwargs = {
                    "query_embeddings": query_embeddings,
                    "n_results": self._max_documents,
                    "include": ["documents", "distances"],
                }
                if where_metadata:
                    kwargs["where"] = where_metadata
                results = self._chroma_collection.query(**kwargs)
                # ... (validações de formato omitidas) ...
                # Chroma cosine: menor distância = mais similar; similaridade = max(0, 1 - distance)
                scored = []
                for doc, dist in zip(doc_list, dist_list):
                    sim = max(0.0, 1.0 - float(dist))
                    if sim >= self._min_similarity_score and doc:
                        scored.append((sim, doc))
                scored.sort(key=lambda x: -x[0])
                return " ".join(d[1] for d in scored)
```

Três decisões de projeto que valem destacar:

**1. Distância vs. similaridade.** O Chroma devolve *distância de cosseno* (`distance = 1 - cos(θ)`): quanto **menor**, mais parecido. O código converte de volta para similaridade (`1 - distance`) para ficar intuitivo:

```
  distância 0.0  →  similaridade 1.0  (idênticos)
  distância 0.4  →  similaridade 0.6  (relacionados)
  distância 0.65 →  similaridade 0.35 (limiar mínimo — abaixo disso, descarta)
```

**2. O limiar `min_similarity_score` evita "alucinação por contexto ruim".** Sem ele, a busca *sempre* devolve os 3 vizinhos mais próximos — mesmo que a pergunta seja "qual a capital da França?" e o banco só tenha tarifas bancárias. O limiar diz: *"se nada for parecido o suficiente, melhor devolver nada"*.

**3. Resiliência: retry + degradação graciosa.** A busca tenta até 3 vezes com espera exponencial (`tenacity`); se tudo falhar, devolve string vazia em vez de derrubar o agente — o agente segue funcionando, só sem memória de longo prazo naquele turno:

```240:248:src/memory_gateway.py
        try:
            return await asyncio.to_thread(
                self._search_customer_insights_sync_retry,
                query,
                where_metadata,
            )
        except Exception:
            logger.warning("Long-Term Memory indisponível após retries. Degradando para contexto vazio.")
            return ""
```

(O `asyncio.to_thread` existe porque a busca é síncrona/pesada e não pode travar o *event loop* do agente.)

---

## Parte 7 — O ponto de entrada do usuário (`scripts/rag_query.py`)

Um script fininho, de propósito: ele só monta o gateway e faz a pergunta. Toda a inteligência está nas camadas anteriores.

```bash
python scripts/rag_query.py "Qual a tarifa da conta premium e condições de empréstimo?"
```

```55:58:scripts/rag_query.py
    gateway = LongTermMemoryGateway(config_path=args.config)
    result = asyncio.run(gateway.search_customer_insights(args.query))

    print(result if result else "(nenhum trecho recuperado)")
```

Saída esperada (os chunks recuperados, concatenados por relevância):

```
Conta premium isenta de taxa de manutenção mensal. Demais contas: R$ 25 TED: isento
para conta premium até 5 por mês. Após isso ... Empréstimo pessoal: taxa a partir de...
```

Em um agente real, esse texto seria injetado no *prompt* do LLM como contexto ("com base nos trechos abaixo, responda...") — mas isso já é assunto da próxima aula.

---

## Resumo: quem faz o quê

| Etapa | Arquivo | Responsabilidade |
|---|---|---|
| Dados | `data/lab/*.pdf/.csv/.txt` | Documentos brutos do banco fictício |
| Config de ingestão | `config/indexing.yaml` | Estratégia/tamanho de chunk, backend/modelo de embedding |
| Config de busca | `config/memory_policy.yaml` | Backend do vector store, `max_documents`, `min_similarity_score` |
| Leitura | `src/indexing/loaders.py` | PDF/CSV/TXT/JSON → `[{"text", "metadata"}]` |
| Corte | `src/indexing/chunking.py` | Texto → chunks (5 estratégias) |
| Vetorização | `src/indexing/embedding.py` | Chunks → vetores de 384 dims (+ `cosine_similarity` didática) |
| Armazenamento | `src/indexing/vector_store.py` | Vetores + textos + metadados → ChromaDB (métrica cosseno) |
| Orquestração da ingestão | `src/indexing/__main__.py` | CLI `python -m src.indexing --input ... --push` |
| Consulta | `src/memory_gateway.py` | Pergunta → embedding → k-vizinhos → filtro por similaridade → texto |
| Interface | `scripts/rag_query.py` | CLI de pergunta ao RAG |
| Lab de análise | `scripts/chunk_inspect.py` | Compara estratégias de chunking com métricas |

## Os 3 conceitos que você precisa levar para casa

1. **Chunking é um trade-off**: pedaços pequenos = busca precisa mas sem contexto; pedaços grandes = contexto rico mas busca borrada. `recursive` com overlap é o equilíbrio pragmático.
2. **Embedding é o GPS do significado**: texto vira vetor; significados parecidos viram vetores vizinhos. Pergunta e documento **precisam usar o mesmo modelo** — senão as "coordenadas" não são comparáveis (por isso trocar de backend exige reindexar).
3. **Cosseno mede direção, não tamanho**: a similaridade olha o *ângulo* entre vetores. `1.0` = mesmo significado, `0.0` = nada a ver, e o limiar (`0.35` aqui) decide quando é melhor devolver nada do que devolver lixo.
