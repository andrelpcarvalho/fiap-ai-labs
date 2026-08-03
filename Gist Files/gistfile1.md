# Estratégias de chunking para RAG multi-formato

Documento de referência com as estratégias de divisão (chunking) de documentos para um pipeline de RAG que precisa lidar com PDF, DOCX, XLS e outros formatos não estruturados.

## Por que o chunking importa tanto quanto o parser

O parser (MarkItDown, Docling, Marker) determina a **qualidade do texto extraído**. O chunking determina **o que o modelo de embedding e o LLM efetivamente enxergam** na hora da busca. Um parser perfeito com um chunking ruim ainda produz um RAG ruim — cortar no lugar errado quebra tabelas, separa uma pergunta da sua resposta, ou junta dois assuntos sem relação em um único chunk.

Regra geral: **o tamanho do chunk é uma decisão de recuperação, não de armazenamento.** Chunks pequenos demais perdem contexto; chunks grandes demais diluem a relevância e estouram a janela do LLM com ruído.

## 1. Chunking por tamanho fixo (baseline, evitar como estratégia única)

Divide o texto em blocos de N caracteres ou tokens, com uma sobreposição (overlap) fixa.

- **Como funciona**: por exemplo, 500 tokens por chunk, 50 de overlap.
- **Vantagem**: simples, rápido, previsível.
- **Problema**: ignora completamente a estrutura do documento — pode cortar uma tabela ao meio, separar um heading do parágrafo que ele introduz, ou quebrar uma frase.
- **Quando usar**: só como fallback, para textos sem nenhuma estrutura reconhecível (ex.: transcrição de áudio corrida).

## 2. Chunking recursivo por delimitador

Tenta dividir primeiro por unidades semânticas maiores (parágrafo → sentença → palavra), aplicando o próximo delimitador só quando o chunk ainda excede o tamanho máximo.

- **Ordem típica de delimitadores**: `\n\n` (parágrafo) → `\n` (linha) → `. ` (sentença) → espaço.
- **Vantagem**: resultado bem mais coerente que o tamanho fixo, sem cortar frases ao meio.
- **Quando usar**: bom default para texto corrido (contratos, artigos, e-mails) quando não há headings claros.

## 3. Chunking hierárquico por heading/seção (recomendado como estratégia principal)

Usa a estrutura do markdown normalizado (H1, H2, H3, listas, tabelas) para definir os limites do chunk, em vez de contar caracteres.

- **Como funciona**: cada chunk carrega o caminho de headings pai (ex.: `Contrato > Cláusula 4 > Condições de pagamento`) como metadado, e o corte acontece nas fronteiras de seção, não no meio dela.
- **Vantagem**: preserva o contexto lógico do documento; o chunk "sabe" de onde veio.
- **Regra prática de tamanho**: 300–800 tokens por chunk, com overlap pequeno (10–15%) só para não perder continuidade entre seções adjacentes.
- **Quando usar**: documentos corporativos, manuais, contratos, relatórios — qualquer coisa com estrutura de headings.

## 4. Chunking consciente de tabela (table-aware)

Tabelas nunca devem ser cortadas por tamanho de texto — uma linha sem o cabeçalho da coluna perde todo o significado.

- **Como funciona**: cada tabela vira um chunk próprio (ou um grupo de chunks se for muito grande), sempre incluindo a linha de cabeçalho repetida em cada pedaço.
- **Para planilhas (XLS/XLSX)**: trate cada aba como uma unidade lógica; se a aba for grande, particione por bloco de linhas mantendo o cabeçalho, nunca por caracteres.
- **Vantagem**: evita o erro mais comum em RAG com dados tabulares — o modelo "inventa" valores porque perdeu a referência da coluna.

## 5. Chunking pai-filho / small-to-big (parent-child)

Indexa dois níveis: um chunk pequeno e preciso para a busca (embedding), e um chunk maior (o "pai": seção inteira ou página) que é o que realmente vai para o LLM.

- **Como funciona**: a busca por similaridade roda sobre os chunks pequenos (mais precisos para casar com a pergunta), mas ao encontrar um chunk pequeno relevante, o pipeline recupera o chunk pai inteiro para dar contexto completo ao LLM.
- **Vantagem**: resolve o dilema entre precisão na busca (chunks pequenos) e contexto suficiente na resposta (chunks grandes) sem escolher só um dos dois.
- **Quando usar**: bases de conhecimento grandes e heterogêneas, onde perguntas específicas precisam de respostas com contexto amplo.

## 6. Chunking semântico (embedding-based)

Em vez de usar delimitadores estruturais, mede a similaridade semântica entre sentenças consecutivas e corta onde o "assunto muda".

- **Como funciona**: gera embedding sentença a sentença, calcula a distância entre sentenças vizinhas, e cria um novo chunk quando a distância ultrapassa um limiar.
- **Vantagem**: captura mudanças de tópico que a estrutura visual do documento não denuncia (ex.: um PDF sem headings claros).
- **Custo**: mais caro computacionalmente (precisa rodar embeddings na fase de ingestão, não só na busca).
- **Quando usar**: documentos com pouca ou nenhuma estrutura hierárquica, mas com múltiplos assuntos misturados no mesmo bloco de texto.

## 7. Chunking agentic (LLM-guided)

Usa um LLM para decidir os limites do chunk, com um prompt que pede para identificar unidades de informação autocontidas.

- **Vantagem**: melhor qualidade possível, especialmente para documentos com estrutura irregular ou raciocínio implícito entre parágrafos.
- **Custo**: o mais caro de todos — cada documento passa por uma chamada de LLM extra na ingestão.
- **Quando usar**: apenas para conjuntos de documentos de alto valor e baixo volume (ex.: contratos críticos), não como estratégia padrão em escala.

## Estratégia recomendada por tipo de conteúdo

| Tipo de conteúdo | Estratégia principal |
|---|---|
| Documentos com headings claros (manuais, relatórios, contratos) | Hierárquico por seção (#3) |
| Tabelas e planilhas (XLS/XLSX) | Table-aware (#4) |
| Texto corrido sem estrutura (e-mails, transcrições) | Recursivo por delimitador (#2) |
| Bases de conhecimento grandes e heterogêneas | Pai-filho / small-to-big (#5) |
| PDFs com estrutura visual fraca, múltiplos assuntos | Semântico (#6) |
| Documentos críticos, baixo volume | Agentic (#7) |

Na prática, um pipeline maduro combina mais de uma: hierárquico como base, table-aware para qualquer tabela detectada, e pai-filho por cima de tudo para equilibrar precisão de busca com contexto de resposta.

## Metadados que todo chunk deve carregar

Independente da estratégia escolhida, cada chunk precisa levar consigo:

- Documento de origem e caminho/URL
- Caminho de headings pai (breadcrumb da seção)
- Número de página (quando aplicável)
- Tipo de documento e data de criação/atualização
- Posição do chunk dentro do documento (para reconstrução de contexto se necessário)

Sem esses metadados, mesmo o melhor chunking perde valor: a resposta final não consegue citar a fonte de forma confiável.
