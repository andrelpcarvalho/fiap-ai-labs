# -*- coding: utf-8 -*-
"""Gera indices_e_vector_stores.html — página didática e profunda."""
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "indices_e_vector_stores.html"

CSS = r"""
body{font-family:Inter,sans-serif;background:#070b14;color:#f8fafc}
.font-mono{font-family:"JetBrains Mono",monospace}
.gradient-text{background:linear-gradient(100deg,#f8fafc 10%,#60a5fa 55%,#34d399);-webkit-background-clip:text;background-clip:text;color:transparent}
.pill{display:inline-flex;align-items:center;gap:.35rem;font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:.2rem .55rem;border-radius:999px;border:1px solid #334155;color:#94a3b8;background:#0f172a}
.pill-accent{border-color:rgba(59,130,246,.4);color:#93c5fd;background:rgba(59,130,246,.1)}
.pill-emerald{border-color:rgba(52,211,153,.4);color:#6ee7b7;background:rgba(52,211,153,.1)}
.pill-amber{border-color:rgba(245,158,11,.4);color:#fcd34d;background:rgba(245,158,11,.1)}
.pill-rose{border-color:rgba(244,63,94,.4);color:#fda4af;background:rgba(244,63,94,.1)}
.pill-violet{border-color:rgba(167,139,250,.4);color:#c4b5fd;background:rgba(167,139,250,.1)}
.card-hover{transition:transform .25s,border-color .25s,box-shadow .25s}
.card-hover:hover{transform:translateY(-3px);border-color:#475569;box-shadow:0 12px 30px -12px rgba(0,0,0,.7)}
.nav-link{transition:all .15s}.nav-link.active{background:rgba(59,130,246,.15);color:#93c5fd;border-color:rgba(59,130,246,.4)}
.story{background:radial-gradient(120% 100% at 0% 0%,rgba(245,158,11,.07),transparent 60%),#0b1220;border:1px solid #1f2937;border-left:3px solid #f59e0b}
.story-punch{border-left:2px solid #f59e0b;background:rgba(245,158,11,.08);color:#fde68a}
.seg-btn.active{background:#1e293b;color:#f8fafc;box-shadow:0 0 0 1px #475569}
canvas.interactive{cursor:crosshair;touch-action:none}
.custom-scroll::-webkit-scrollbar{width:6px}.custom-scroll::-webkit-scrollbar-thumb{background:#334155;border-radius:4px}
pre.code{background:#020617;border:1px solid #1e293b;border-radius:.75rem;padding:1rem;overflow-x:auto;font-size:.75rem;line-height:1.65;color:#cbd5e1}
pre.code .c{color:#64748b}pre.code .s{color:#6ee7b7}pre.code .k{color:#93c5fd}pre.code .n{color:#fcd34d}
input[type=range]{accent-color:#3b82f6}
"""

def main():
    parts = []
    parts.append(f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Índices e Vector Stores — Do zero à referência</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>{CSS}</style>
</head>
<body class="min-h-screen">
<header class="sticky top-0 z-50 border-b border-slate-800 bg-[#070b14]/90 backdrop-blur-md">
  <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
    <div class="flex items-center gap-3">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-blue-500 text-sm font-bold text-slate-900">I</div>
      <div>
        <div class="text-sm font-semibold">Índices e Vector Stores</div>
        <div class="text-[11px] text-slate-500">Do mapa de embeddings à busca em produção</div>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <a href="embeddings_do_zero.html" class="hidden text-xs text-slate-400 hover:text-blue-300 sm:inline">← Embeddings</a>
      <a href="rag_agentic.html#indices" class="hidden text-xs text-slate-400 hover:text-blue-300 md:inline">Masterclass →</a>
      <button id="menuToggle" class="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 lg:hidden">Capítulos</button>
    </div>
  </div>
</header>
<div class="mx-auto flex max-w-7xl gap-8 px-4 py-8">
<aside id="sidebar" class="custom-scroll fixed inset-y-0 left-0 z-40 w-72 -translate-x-full overflow-y-auto border-r border-slate-800 bg-[#070b14] p-5 pt-20 transition-transform lg:sticky lg:top-20 lg:z-0 lg:h-[calc(100vh-6rem)] lg:w-60 lg:translate-x-0 lg:border-0 lg:bg-transparent lg:p-0 lg:pt-0">
  <div class="mb-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">A jornada</div>
  <nav class="flex flex-col gap-1 text-sm" id="chapterNav"></nav>
  <div class="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400">
    Embeddings: <a class="text-blue-300 hover:underline" href="embeddings_do_zero.html">embeddings_do_zero.html</a>. Aqui: navegar o mapa e onde guardá-lo.
  </div>
</aside>
<div id="sidebarOverlay" class="fixed inset-0 z-30 hidden bg-black/60 lg:hidden"></div>
<main class="min-w-0 flex-1 space-y-16 pb-24">
""")

    parts.append("""
<section class="space-y-5">
  <span class="pill pill-amber">Arquivo dedicado · referência</span>
  <h1 class="text-3xl font-extrabold leading-tight sm:text-4xl lg:text-5xl">
    Índices, <span class="gradient-text">Vector Stores</span> e busca aproximada
  </h1>
  <p class="max-w-2xl text-lg text-slate-300">
    Você já sabe o que é um embedding: um endereço numérico de significado.
    Agora a pergunta muda: <b class="text-white">com milhões de endereços, como achar o vizinho certo em milissegundos — e onde guardar tudo isso?</b>
  </p>
  <p class="max-w-2xl text-slate-400">
    Índices merecem arquivo próprio. Aqui vamos do ANN até Vector Stores reais, com fichas profundas de
    <b class="text-emerald-300">ChromaDB</b> e do ecossistema
    <b class="text-blue-300">Gemini Enterprise</b> (File Search, Agent Search, Vertex AI Vector Search, RAG Engine).
  </p>
  <div class="flex flex-wrap gap-2">
    <a href="#vs1" class="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500">Começar →</a>
    <a href="#vs6" class="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500">ChromaDB</a>
    <a href="#vs7" class="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500">Gemini Enterprise</a>
  </div>
</section>
""")

    parts.append("""
<section id="vs1" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 1</span><span class="pill pill-rose">O problema</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Por que o índice existe</h2>
  <div class="story rounded-xl p-5 space-y-3">
    <p>Cada documento virou um ponto num mapa (isso o embedding já fez). Você quer a padaria mais perto da pergunta.</p>
    <p>Opção A: visitar <b class="text-amber-200">todas as casas do país</b>. Sempre certa. Absurdamente lenta — custo <span class="font-mono text-rose-300">O(N × d)</span>.</p>
    <p>Opção B: usar <b class="text-amber-200">atalhos</b> (bairros, grafos, árvores). Pode errar 1–5%. Chega em milissegundos.</p>
    <div class="story-punch mt-3 rounded-r-lg px-4 py-3 text-sm">
      Embedding cria o mapa. Índice navega o mapa. Vector Store é o prédio onde mapa + documentos + etiquetas moram juntos.
    </div>
  </div>
  <div class="grid gap-3 sm:grid-cols-2">
    <div class="rounded-xl border border-rose-900/40 bg-rose-950/15 p-4">
      <div class="text-xs font-bold uppercase tracking-wider text-rose-300 mb-2">Busca exata</div>
      <p class="text-sm text-slate-400">Compara com todos. Recall 100%. Inviável acima de ~100 mil vetores em latência interativa.</p>
    </div>
    <div class="rounded-xl border border-emerald-900/40 bg-emerald-950/15 p-4">
      <div class="text-xs font-bold uppercase tracking-wider text-emerald-300 mb-2">ANN</div>
      <p class="text-sm text-slate-400"><b class="text-white">Approximate Nearest Neighbor</b>. O 1–5% perdido aqui o reranker/LLM <b class="text-slate-200">nunca recuperam</b>.</p>
    </div>
  </div>
</section>
""")

    parts.append("""
<section id="vs2" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 2</span><span class="pill pill-accent">Conceito</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">O que é um Vector Store</h2>
  <p class="text-slate-300 max-w-3xl">Uma lib ANN (Faiss, HNSWlib) só busca vizinhos. Um <b class="text-white">Vector Store</b> é um sistema de dados: vetor + texto + metadata + IDs, com API, persistência e filtros.</p>
  <div class="grid gap-3 sm:grid-cols-4 text-center text-xs">
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div class="font-semibold text-blue-300 mb-1">Vetor</div><div class="text-slate-500">embedding</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div class="font-semibold text-emerald-300 mb-1">Documento</div><div class="text-slate-500">texto original</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div class="font-semibold text-amber-300 mb-1">Metadata</div><div class="text-slate-500">tags filtráveis</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div class="font-semibold text-violet-300 mb-1">ID</div><div class="text-slate-500">chave estável</div></div>
  </div>
  <div class="overflow-x-auto rounded-2xl border border-slate-800">
    <table class="w-full text-left text-xs">
      <thead><tr class="border-b border-slate-800 text-slate-500 bg-slate-950/50">
        <th class="px-4 py-3">Camada</th><th class="px-4 py-3">Exemplos</th><th class="px-4 py-3">Entrega</th><th class="px-4 py-3">Ops</th>
      </tr></thead>
      <tbody class="text-slate-300">
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 font-semibold">Lib ANN</td><td class="px-4 py-3 text-slate-400">Faiss, HNSWlib</td><td class="px-4 py-3 text-slate-400">Só k-NN</td><td class="px-4 py-3 text-slate-400">Você monta tudo</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 font-semibold">Extensão SQL</td><td class="px-4 py-3 text-slate-400">pgvector, AlloyDB</td><td class="px-4 py-3 text-slate-400">Vetores + SQL</td><td class="px-4 py-3 text-slate-400">Baixa se já tem PG</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 font-semibold">Vector DB OSS</td><td class="px-4 py-3 text-slate-400">Chroma, Qdrant, Weaviate, Milvus</td><td class="px-4 py-3 text-slate-400">API + filtros</td><td class="px-4 py-3 text-slate-400">Self-host / cloud</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 font-semibold">Managed</td><td class="px-4 py-3 text-slate-400">Pinecone, Vertex AI Vector Search</td><td class="px-4 py-3 text-slate-400">Escala + SLA</td><td class="px-4 py-3 text-slate-400">Paga serviço</td></tr>
        <tr><td class="px-4 py-3 font-semibold">RAG managed</td><td class="px-4 py-3 text-slate-400">Gemini File Search, Vertex AI Search</td><td class="px-4 py-3 text-slate-400">Pipeline inteiro</td><td class="px-4 py-3 text-slate-400">Mínima · menos controle</td></tr>
      </tbody>
    </table>
  </div>
</section>
""")

    parts.append("""
<section id="vs3" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 3</span><span class="pill pill-amber">Siglas</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Famílias ANN — ficha de referência</h2>
  <div class="overflow-x-auto rounded-2xl border border-slate-800">
    <table class="w-full text-left text-xs">
      <thead><tr class="border-b border-slate-800 text-slate-500 bg-slate-950/50">
        <th class="px-3 py-3">Sigla</th><th class="px-3 py-3">Nome</th><th class="px-3 py-3">Ideia</th><th class="px-3 py-3">Use quando</th>
      </tr></thead>
      <tbody class="text-slate-300">
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono text-rose-300">Flat</td><td class="px-3 py-2.5">Exact / Brute-force</td><td class="px-3 py-2.5 text-slate-400">Compara com todos</td><td class="px-3 py-2.5 text-slate-400">&lt;100k · recall 100%</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono">ANN</td><td class="px-3 py-2.5">Approximate Nearest Neighbor</td><td class="px-3 py-2.5 text-slate-400">Categoria</td><td class="px-3 py-2.5 text-slate-400">Guarda-chuva</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono text-amber-300">IVF</td><td class="px-3 py-2.5">Inverted File Index</td><td class="px-3 py-2.5 text-slate-400">Bairros/células · nprobe</td><td class="px-3 py-2.5 text-slate-400">RAM apertada</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono text-amber-300">PQ</td><td class="px-3 py-2.5">Product Quantization</td><td class="px-3 py-2.5 text-slate-400">Comprime vetores</td><td class="px-3 py-2.5 text-slate-400">IVF-PQ</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono text-blue-300">HNSW</td><td class="px-3 py-2.5">Hierarchical Navigable Small World</td><td class="px-3 py-2.5 text-slate-400">Grafo em camadas</td><td class="px-3 py-2.5 text-slate-400">Padrão em RAM</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 font-mono text-violet-300">DiskANN</td><td class="px-3 py-2.5">Disk-based ANN</td><td class="px-3 py-2.5 text-slate-400">Grafo no SSD</td><td class="px-3 py-2.5 text-slate-400">Bilhões</td></tr>
        <tr><td class="px-3 py-2.5 font-mono text-emerald-300">Tree-AH</td><td class="px-3 py-2.5">Shallow Tree + Asymmetric Hashing</td><td class="px-3 py-2.5 text-slate-400">Árvore + hashing (Google)</td><td class="px-3 py-2.5 text-slate-400">Vertex AI Vector Search</td></tr>
      </tbody>
    </table>
  </div>

  <article class="rounded-2xl border border-blue-900/40 overflow-hidden">
    <div class="border-b border-blue-900/30 bg-blue-950/20 px-5 py-4 flex flex-wrap gap-3 items-center">
      <span class="pill pill-accent">Padrão de mercado</span>
      <h3 class="text-lg font-bold">HNSW — Hierarchical Navigable Small World</h3>
    </div>
    <div class="p-5 space-y-4 text-sm">
      <ul class="space-y-2 text-xs text-slate-400">
        <li><b class="text-blue-300">Hierarchical</b> — camadas (zoom de mapa).</li>
        <li><b class="text-blue-300">Navigable</b> — caminha pelas arestas até a região certa.</li>
        <li><b class="text-blue-300">Small World</b> — poucos saltos ligam pontos distantes.</li>
      </ul>
      <p class="text-xs text-slate-500">Paper: Malkov &amp; Yashunin, 2018. Analogia: avião → ônibus → a pé.</p>
      <div class="grid gap-2 sm:grid-cols-3 text-xs">
        <div class="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span class="font-mono text-blue-300">M</span><div class="mt-1 text-slate-500">conexões/nó · ↑ recall ↑ RAM</div></div>
        <div class="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span class="font-mono text-blue-300">efConstruction</span><div class="mt-1 text-slate-500">qualidade na construção</div></div>
        <div class="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span class="font-mono text-blue-300">efSearch</span><div class="mt-1 text-slate-500">botão recall × latência</div></div>
      </div>
      <div class="grid sm:grid-cols-2 gap-3 text-xs">
        <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3"><b class="text-emerald-300">Usar:</b> RAG com índice em RAM — Chroma, pgvector, Qdrant, Weaviate.</div>
        <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-3"><b class="text-rose-300">Evitar:</b> bilhões sem RAM; deleções agressivas (tombstones).</div>
      </div>
    </div>
  </article>

  <article class="rounded-2xl border border-amber-900/40 overflow-hidden">
    <div class="border-b border-amber-900/30 bg-amber-950/20 px-5 py-4 flex flex-wrap gap-3 items-center">
      <span class="pill pill-amber">Partição</span>
      <h3 class="text-lg font-bold">IVF / IVF-PQ</h3>
    </div>
    <div class="p-5 text-xs text-slate-400 leading-relaxed space-y-3">
      <p><b class="text-amber-300">IVF</b> (Inverted File): k-means cria <span class="font-mono">nlist</span> células; na query visita <span class="font-mono">nprobe</span>. <b class="text-amber-300">PQ</b> (Product Quantization): comprime vetores 10–50×. Dupla clássica Faiss/Milvus.</p>
      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3"><b class="text-emerald-300">Usar:</b> milhões de vetores, RAM cara, rescoring ok.</div>
        <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-3"><b class="text-rose-300">Evitar:</b> corpus pequeno; nprobe sem medição.</div>
      </div>
    </div>
  </article>

  <article class="rounded-2xl border border-emerald-900/40 overflow-hidden">
    <div class="border-b border-emerald-900/30 bg-emerald-950/20 px-5 py-4 flex flex-wrap gap-3 items-center">
      <span class="pill pill-emerald">Google</span>
      <h3 class="text-lg font-bold">Tree-AH — algoritmo do Vertex AI Vector Search</h3>
    </div>
    <div class="p-5 text-xs text-slate-400 leading-relaxed space-y-3">
      <p>Padrão do <b class="text-white">Vertex AI Vector Search</b> (ex-Matching Engine). Paper arXiv 1908.10396.</p>
      <ul class="list-disc list-inside space-y-1">
        <li><b class="text-emerald-300">Shallow tree</b> — partição hierárquica rasa (ideia de “bairros”).</li>
        <li><b class="text-emerald-300">Asymmetric Hashing</b> — banco comprimido; query em precisão maior na comparação.</li>
      </ul>
      <p>Params: <span class="font-mono text-emerald-300">leaf_node_embedding_count</span>, <span class="font-mono text-emerald-300">leaf_nodes_to_search_percent</span>, <span class="font-mono text-emerald-300">approximate_neighbors_count</span>. Alternativa no mesmo produto: <b class="text-white">BruteForce</b>.</p>
      <p class="text-slate-500">HNSW = grafo (OSS). Tree-AH = partição+hashing otimizado para serving distribuído Google. Ambos são ANN.</p>
    </div>
  </article>

  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 text-xs">
    <h3 class="font-semibold text-sm mb-3">Guia por tamanho</h3>
    <table class="w-full text-left text-slate-300">
      <tr class="border-b border-slate-800"><td class="py-2 text-slate-400">&lt; 100 mil</td><td>Força bruta</td></tr>
      <tr class="border-b border-slate-800"><td class="py-2 text-slate-400">10⁵–10⁷ em RAM</td><td class="text-blue-300">HNSW</td></tr>
      <tr class="border-b border-slate-800"><td class="py-2 text-slate-400">Milhões · RAM cara</td><td class="text-amber-300">IVF-PQ</td></tr>
      <tr class="border-b border-slate-800"><td class="py-2 text-slate-400">GCP · escala alta</td><td class="text-emerald-300">Tree-AH</td></tr>
      <tr><td class="py-2 text-slate-400">Bilhões</td><td class="text-violet-300">DiskANN / VS sharded</td></tr>
    </table>
  </div>
</section>
""")

    # VS4 playground + VS5 chart - continue in next append
    parts.append(VS4_VS5())
    parts.append(VS6_CHROMA())
    parts.append(VS7_GEMINI())
    parts.append(VS8_VS9())
    parts.append(SCRIPT())

    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


def VS4_VS5():
    return r"""
<section id="vs4" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 4</span><span class="pill pill-amber">Brinquedo</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Ache o vizinho — ao vivo</h2>
  <p class="text-sm text-slate-400">Clique no mapa (estrela = consulta). Compare força bruta × IVF × HNSW: quantas casas visitou e se achou o vizinho verdadeiro.</p>
  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
    <div class="flex flex-wrap gap-2">
      <button class="ann-mode seg-btn active rounded-lg border border-slate-700 px-3 py-1.5 text-sm" data-mode="brute">Força bruta</button>
      <button class="ann-mode seg-btn rounded-lg border border-slate-700 px-3 py-1.5 text-sm" data-mode="ivf">Bairros (IVF)</button>
      <button class="ann-mode seg-btn rounded-lg border border-slate-700 px-3 py-1.5 text-sm" data-mode="hnsw">Atalhos (HNSW)</button>
    </div>
    <div id="ivfControls" class="hidden items-center gap-3 text-sm">
      <label class="flex flex-1 items-center gap-3 text-slate-300">
        <span>nprobe: <span id="nprobeVal" class="font-mono text-blue-300">3</span></span>
        <input id="nprobe" type="range" min="1" max="9" value="3" class="flex-1"/>
      </label>
    </div>
    <canvas id="annCanvas" class="interactive w-full rounded-xl border border-slate-700 bg-[#0b1220]" height="420"></canvas>
    <div class="flex flex-wrap gap-2">
      <button id="annSearchBtn" class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500">Buscar vizinho</button>
      <button id="annResetBtn" class="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300">Novo mapa</button>
    </div>
    <div class="grid gap-3 sm:grid-cols-4">
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-center"><div class="text-[10px] uppercase text-slate-500">Comparações</div><div id="annComparisons" class="mt-1 font-mono text-xl text-blue-300">—</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-center"><div class="text-[10px] uppercase text-slate-500">Tempo</div><div id="annTime" class="mt-1 font-mono text-xl text-amber-300">—</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-center"><div class="text-[10px] uppercase text-slate-500">Achou?</div><div id="annRecall" class="mt-1 text-xl font-semibold text-slate-400">—</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-center"><div class="text-[10px] uppercase text-slate-500">Estratégia</div><div id="annStrategy" class="mt-1 text-sm font-semibold">—</div></div>
    </div>
    <div id="annExplain" class="rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">Clique no mapa…</div>
  </div>
</section>

<section id="vs5" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 5</span><span class="pill pill-rose">Métricas</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Recall × velocidade</h2>
  <div class="grid gap-3 sm:grid-cols-2">
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-400">
      <div class="text-sm font-semibold text-emerald-300 mb-2">Recall do ANN</div>
      Resultado aproximado vs busca exata. “O índice está calibrado?”
    </div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-400">
      <div class="text-sm font-semibold text-blue-300 mb-2">Recall do sistema</div>
      Recuperado vs o que um humano marcou como certo. Mede embedding + chunking + índice.
    </div>
  </div>
  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
    <div class="relative w-full" style="height:320px"><canvas id="annChart"></canvas></div>
    <p class="mt-3 text-xs text-slate-500">Índice com recall 0,99 sobre embeddings ruins = lixo rápido. As duas engrenagens precisam estar boas.</p>
  </div>
</section>
"""


def VS6_CHROMA():
    return r"""
<section id="vs6" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 6</span><span class="pill pill-emerald">ChromaDB</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">ChromaDB — referência completa</h2>

  <div class="story rounded-xl p-5 space-y-3">
    <p>Antes do Chroma, o menu era: Faiss (só índice), Milvus/Weaviate (infra pesada) ou Pinecone (pago). Faltava o “Postgres do embedding” para quem quer <b class="text-amber-200">pip install e já busca</b>.</p>
    <p>Fundado em 2022 por Jeff Huber e Anton Troynikov com tese clara: <b class="text-white">developer experience first</b>. Defaults sensatos: HNSW + SQLite + embedding function embutida.</p>
    <div class="story-punch mt-3 rounded-r-lg px-4 py-3 text-sm">
      Analogia: um armário mágico. Cada pasta tem sensor de significado. Você descreve a ideia — o armário desliza as pastas mais parecidas. Por baixo: embeddings + HNSW + metadata.
    </div>
  </div>

  <div>
    <h3 class="font-semibold mb-3">A unidade de dado: o trio</h3>
    <div class="grid gap-3 sm:grid-cols-3 text-xs">
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-blue-300">embedding</b><div class="mt-1 text-slate-500">vetor denso (ex.: 384D MiniLM)</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-emerald-300">document</b><div class="mt-1 text-slate-500">texto bruto devolvido na query</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-amber-300">metadata</b><div class="mt-1 text-slate-500">tags: status, produto, tenant…</div></div>
    </div>
    <p class="mt-3 text-xs text-slate-500">Mais o <span class="font-mono">id</span>. Muitos bancos só guardam vetor+id; o Chroma colocaliza os três — um insert, uma query, tudo volta junto.</p>
  </div>

  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
    <h3 class="font-semibold">Arquitetura interna (o que mora no disco)</h3>
    <p class="text-xs text-slate-400 leading-relaxed">Desde ~v1.0 o núcleo de performance (HNSW, segmentos, query) migrou para <b class="text-white">Rust</b>. Separação chave:</p>
    <div class="grid gap-3 md:grid-cols-2 text-xs">
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
        <div class="font-semibold text-emerald-300">SQLite — chroma.sqlite3</div>
        <ul class="text-slate-400 space-y-1 list-disc list-inside">
          <li>Sysdb: tenants, databases, collections, segments</li>
          <li>Metadata segment: documentos + key-values</li>
          <li>FTS5 para <span class="font-mono">where_document</span></li>
          <li>WAL para durabilidade</li>
        </ul>
      </div>
      <div class="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
        <div class="font-semibold text-blue-300">Pasta UUID por collection — HNSW</div>
        <ul class="text-slate-400 space-y-1 list-disc list-inside">
          <li><span class="font-mono">header.bin</span> — params/estrutura</li>
          <li><span class="font-mono">link_lists.bin</span> — adjacências</li>
          <li><span class="font-mono">data_level0.bin</span> — camada base + vetores</li>
          <li><span class="font-mono">index_metadata.pickle</span> — mapa id ↔ label</li>
        </ul>
      </div>
    </div>
    <p class="text-xs text-slate-500">Cada collection tem dois segments: <b class="text-slate-300">metadata</b> e <b class="text-slate-300">vector</b>. Query: embed → HNSW ANN → pós-filtro SQL → devolve docs.</p>
  </div>

  <div>
    <h3 class="font-semibold mb-3">Quatro modos de deploy</h3>
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-slate-200">Ephemeral</b><div class="mt-1 text-slate-500">Só RAM. Some ao sair. Ideal para testes.</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-slate-200">Persistent</b><div class="mt-1 text-slate-500">Pasta no disco. Labs e apps locais.</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-slate-200">HttpClient</b><div class="mt-1 text-slate-500">Server separado. Time compartilhando índice.</div></div>
      <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-slate-200">Chroma Cloud</b><div class="mt-1 text-slate-500">Gerenciado pelo vendor.</div></div>
    </div>
  </div>

  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
    <h3 class="font-semibold">Collection + parâmetros HNSW</h3>
<pre class="code"><span class="k">import</span> chromadb
client = chromadb.PersistentClient(path=<span class="s">"./chroma_data"</span>)
collection = client.create_collection(
    name=<span class="s">"politicas"</span>,
    metadata={
        <span class="s">"hnsw:space"</span>: <span class="s">"cosine"</span>,          <span class="c"># l2 | ip | cosine</span>
        <span class="s">"hnsw:M"</span>: <span class="n">16</span>,                   <span class="c"># conexões por nó</span>
        <span class="s">"hnsw:construction_ef"</span>: <span class="n">100</span>,  <span class="c"># qualidade do grafo</span>
        <span class="s">"hnsw:search_ef"</span>: <span class="n">100</span>,         <span class="c"># recall × latência</span>
    },
)</pre>
    <div class="grid gap-2 sm:grid-cols-2 text-xs text-slate-400">
      <div><span class="font-mono text-blue-300">hnsw:space</span> — métrica. Em RAG costuma ser <span class="font-mono">cosine</span>.</div>
      <div><span class="font-mono text-blue-300">M</span> — mais conexões = melhor recall, mais RAM.</div>
      <div><span class="font-mono text-blue-300">construction_ef</span> — pago na indexação; grafo mais cuidadoso.</div>
      <div><span class="font-mono text-blue-300">search_ef</span> — pago na query; aumente até o recall estabilizar.</div>
    </div>
  </div>

  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
    <h3 class="font-semibold">API essencial + o perigo do pós-filtro</h3>
<pre class="code">collection.add(
    ids=[<span class="s">"doc-1"</span>, <span class="s">"doc-2"</span>],
    documents=[<span class="s">"Carência de 45 dias…"</span>, <span class="s">"Seguro prestamista…"</span>],
    metadatas=[{<span class="s">"status"</span>: <span class="s">"vigente"</span>, <span class="s">"produto"</span>: <span class="s">"credito"</span>},
               {<span class="s">"status"</span>: <span class="s">"revogado"</span>, <span class="s">"produto"</span>: <span class="s">"credito"</span>}],
)
results = collection.query(
    query_texts=[<span class="s">"qual o prazo de carência?"</span>],
    n_results=<span class="n">5</span>,
    where={<span class="s">"status"</span>: <span class="s">"vigente"</span>, <span class="s">"produto"</span>: <span class="s">"credito"</span>},
    where_document={<span class="s">"$contains"</span>: <span class="s">"dias"</span>},
)</pre>
    <div class="rounded-xl border border-amber-900/40 bg-amber-950/15 p-4 text-xs text-slate-300 leading-relaxed">
      <b class="text-amber-300">Atenção (pós-filtro):</b> o Chroma tipicamente busca candidatos no HNSW e <b>depois</b> aplica o <span class="font-mono">where</span> no SQLite.
      Se o filtro for muito seletivo, pode voltar <b>menos</b> que <span class="font-mono">n_results</span> — ou quase nada.
      É o mesmo bug de família da “norma revogada” do módulo avançado: a ordem entre filtrar e ranquear importa.
      Em produção, meça recall <b>com o filtro ligado</b>.
    </div>
  </div>

  <div class="grid gap-3 sm:grid-cols-2 text-xs">
    <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-4 space-y-2">
      <div class="font-semibold text-emerald-300">Quando usar Chroma</div>
      <ul class="text-slate-400 space-y-1 list-disc list-inside">
        <li>Aulas, labs, protótipos RAG</li>
        <li>Apps até alguns milhões de vetores</li>
        <li>Soberania de dados / on-prem / VPC</li>
        <li>Qualquer modelo de embedding (BYO)</li>
        <li>Time pequeno sem plataforma GCP</li>
      </ul>
    </div>
    <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-4 space-y-2">
      <div class="font-semibold text-rose-300">Quando NÃO usar</div>
      <ul class="text-slate-400 space-y-1 list-disc list-inside">
        <li>Bilhões de vetores / multi-região gerenciada</li>
        <li>SLA enterprise sem equipe de ops</li>
        <li>Precisa de Tree-AH / serving Google nativo</li>
        <li>Quer pipeline “upload PDF → resposta” sem código</li>
      </ul>
    </div>
  </div>

  <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-400 space-y-2">
    <div class="font-semibold text-slate-200">Manutenção do HNSW</div>
    <p>Com o tempo o grafo fragmenta (deletes lógicos). Ferramentas do cookbook: <span class="font-mono text-blue-300">hnsw info</span> (fragmentação, WAL gap, orphan labels) e <span class="font-mono text-blue-300">hnsw rebuild</span> (reconstrói e permite mudar params de construção).</p>
  </div>
</section>
"""


def VS7_GEMINI():
    return r"""
<section id="vs7" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 7</span><span class="pill pill-accent">Gemini Enterprise</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Vector Stores no ecossistema Gemini Enterprise</h2>

  <div class="story rounded-xl p-5 space-y-3">
    <p>No Google Cloud, “vector store” não é um único produto — é uma <b class="text-amber-200">escada de controle</b>.
    Em 2025–2026, Vertex AI e Agentspace convergem sob a marca <b class="text-white">Gemini Enterprise / Agent Platform</b>.
    O que muda é o marketing; as peças de retrieval continuam distintas e você precisa escolher a camada certa.</p>
    <div class="story-punch mt-3 rounded-r-lg px-4 py-3 text-sm">
      Quanto mais gerenciado, menos você mexe em chunking/HNSW — e menos controle tem. Quanto mais “vector store de verdade”, mais ops e mais precisão de engenharia.
    </div>
  </div>

  <div class="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
    <h3 class="font-semibold mb-4">Mapa mental — do mais gerenciado ao mais controle</h3>
    <div class="space-y-2 text-xs">
      <div class="flex gap-3 items-start rounded-lg border border-blue-900/40 bg-blue-950/20 p-3"><span class="font-mono text-blue-300 w-6">1</span><div><b class="text-white">Gemini File Search Store</b> — upload → Google chunka, embeda, indexa, cita.</div></div>
      <div class="flex gap-3 items-start rounded-lg border border-cyan-900/40 bg-cyan-950/10 p-3"><span class="font-mono text-cyan-300 w-6">2</span><div><b class="text-white">Agent Search / Vertex AI Search</b> — busca enterprise + grounding “Your data”.</div></div>
      <div class="flex gap-3 items-start rounded-lg border border-emerald-900/40 bg-emerald-950/10 p-3"><span class="font-mono text-emerald-300 w-6">3</span><div><b class="text-white">RAG Engine</b> — pipeline managed; pode plugar Vector Search atrás.</div></div>
      <div class="flex gap-3 items-start rounded-lg border border-amber-900/40 bg-amber-950/10 p-3"><span class="font-mono text-amber-300 w-6">4</span><div><b class="text-white">Vertex AI Vector Search</b> — índice ANN gerenciado (Tree-AH); você traz embeddings.</div></div>
      <div class="flex gap-3 items-start rounded-lg border border-violet-900/40 bg-violet-950/10 p-3"><span class="font-mono text-violet-300 w-6">5</span><div><b class="text-white">BYO</b> — AlloyDB (pgvector+ScaNN), BigQuery vectors, Elasticsearch grounding.</div></div>
    </div>
  </div>

  <!-- Layer 1 -->
  <article class="rounded-2xl border border-blue-900/40 overflow-hidden">
    <div class="border-b border-blue-900/30 bg-blue-950/20 px-5 py-4">
      <span class="pill pill-accent">Camada 1 · máximo managed</span>
      <h3 class="mt-2 text-lg font-bold">Gemini File Search / File Search Store</h3>
    </div>
    <div class="p-5 space-y-3 text-xs text-slate-400 leading-relaxed">
      <p>Um <b class="text-white">File Search Store</b> funciona como vector database gerenciado dentro da API Gemini.
      Você sobe arquivos; o Google cuida de OCR/chunking/embeddings/índice/retrieval e devolve respostas com <b class="text-slate-200">citações</b>.
      Suporta multimodal e filtros de metadata — sem você escolher HNSW vs IVF.</p>
      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3"><b class="text-emerald-300">Usar:</b> Q&amp;A sobre docs em horas; POC; assistente interno simples; time sem infra de retrieval.</div>
        <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-3"><b class="text-rose-300">Evitar:</b> precisa controlar chunk size/overlap; embedding custom; multi-cloud; auditoria fina do índice.</div>
      </div>
      <p class="text-slate-500">Trade-off central: velocidade de entrega × lock-in e opacidade do pipeline.</p>
    </div>
  </article>

  <!-- Layer 2 -->
  <article class="rounded-2xl border border-cyan-900/40 overflow-hidden">
    <div class="border-b border-cyan-900/30 bg-cyan-950/15 px-5 py-4">
      <span class="pill" style="border-color:rgba(34,211,238,.4);color:#67e8f9;background:rgba(34,211,238,.1)">Camada 2 · busca enterprise</span>
      <h3 class="mt-2 text-lg font-bold">Agent Search / Vertex AI Search (AI Applications)</h3>
    </div>
    <div class="p-5 space-y-3 text-xs text-slate-400 leading-relaxed">
      <p>Motor de busca gerenciado sobre <b class="text-white">data stores</b> (sites ou documentos).
      É a peça de <b class="text-slate-200">grounding “Your data”</b> no Gemini Enterprise Agent Platform:
      o modelo consulta sua base e cita trechos. Dá para combinar com Google Search grounding.
      Limite típico: até ~10 fontes de dados no grounding.</p>
      <p>Diferente do Vector Search “cru”: aqui você compra <b class="text-white">experiência de busca Google</b> (ranking, permissões, conectores), não só k-NN de vetores.</p>
      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3"><b class="text-emerald-300">Usar:</b> assistente corporativo; intranet; docs com ACL; quando “search quality” &gt; controle de embedding.</div>
        <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-3"><b class="text-rose-300">Evitar:</b> precisa do seu modelo de embedding; lógica de retrieval muito custom; custo de grounding por query sem orçamento.</div>
      </div>
    </div>
  </article>

  <!-- Layer 3 RAG Engine -->
  <article class="rounded-2xl border border-emerald-900/40 overflow-hidden">
    <div class="border-b border-emerald-900/30 bg-emerald-950/15 px-5 py-4">
      <span class="pill pill-emerald">Camada 3 · pipeline</span>
      <h3 class="mt-2 text-lg font-bold">RAG Engine</h3>
    </div>
    <div class="p-5 text-xs text-slate-400 leading-relaxed space-y-2">
      <p>Pipeline managed: ingest → chunk → embed → retrieve. Meio-termo entre File Search (tudo opaco) e DIY total.
      Pode associar um índice de <b class="text-white">Vertex AI Vector Search</b> (exige <span class="font-mono">STREAM_UPDATE</span> no índice compatível com o corpus).</p>
    </div>
  </article>

  <!-- Layer 4 Vector Search -->
  <article class="rounded-2xl border border-amber-900/40 overflow-hidden">
    <div class="border-b border-amber-900/30 bg-amber-950/20 px-5 py-4">
      <span class="pill pill-amber">Camada 4 · vector store de verdade no GCP</span>
      <h3 class="mt-2 text-lg font-bold">Vertex AI Vector Search (ex-Matching Engine)</h3>
    </div>
    <div class="p-5 space-y-4 text-xs text-slate-400 leading-relaxed">
      <p>Aqui <b class="text-white">você</b> gera embeddings e o Google serve o índice em nós.
      Custo típico: <b class="text-slate-200">node-hour</b> (máquina + réplicas), não “centavos por query” isolados.</p>

      <div>
        <div class="font-semibold text-slate-200 mb-2">Algoritmos</div>
        <ul class="list-disc list-inside space-y-1">
          <li><b class="text-amber-300">Tree-AH</b> — padrão produção (árvore rasa + hashing assimétrico).</li>
          <li><b class="text-amber-300">BruteForce</b> — exato; baseline ou índices menores.</li>
        </ul>
      </div>

      <div>
        <div class="font-semibold text-slate-200 mb-2">Atualização do índice (escolha imutável na criação)</div>
        <div class="grid sm:grid-cols-2 gap-3">
          <div class="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span class="font-mono text-amber-300">BATCH_UPDATE</span><div class="mt-1">Delta via GCS; bom para jobs semanais/mensais.</div></div>
          <div class="rounded-lg border border-slate-800 bg-slate-950/50 p-3"><span class="font-mono text-amber-300">STREAM_UPDATE</span><div class="mt-1">upsert/delete quase real-time; obrigatório p/ RAG Engine.</div></div>
        </div>
        <p class="mt-2 text-slate-500">Não dá para converter batch→stream: cria-se um índice novo. Streaming tem custo extra de update e compactação periódica.</p>
      </div>

      <div>
        <div class="font-semibold text-slate-200 mb-2">Ciclo de vida</div>
        <p><span class="font-mono">Index</span> → <span class="font-mono">IndexEndpoint</span> → <span class="font-mono">DeployedIndex</span> (réplicas, machine type).
        Filtros: <b class="text-slate-200">restricts</b> / numeric restricts nos datapoints (o equivalente Google aos metadados filtráveis).</p>
      </div>

<pre class="code"><span class="c"># Conceito — criar índice Tree-AH com streaming</span>
index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name=<span class="s">"rag-credito"</span>,
    dimensions=<span class="n">768</span>,
    approximate_neighbors_count=<span class="n">150</span>,
    leaf_node_embedding_count=<span class="n">500</span>,
    leaf_nodes_to_search_percent=<span class="n">7</span>,
    distance_measure_type=<span class="s">"DOT_PRODUCT_DISTANCE"</span>,
    index_update_method=<span class="s">"STREAM_UPDATE"</span>,
)</pre>

      <div class="grid sm:grid-cols-2 gap-3">
        <div class="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3"><b class="text-emerald-300">Usar:</b> dezenas de milhões de vetores; embedding custom; latência baixa; já está no GCP; RAG Engine com VS.</div>
        <div class="rounded-xl border border-rose-900/30 bg-rose-950/10 p-3"><b class="text-rose-300">Evitar:</b> lab de aula; orçamento sem nó dedicado; quer só “subir PDF”; multi-cloud portátil.</div>
      </div>
    </div>
  </article>

  <!-- Layer 5 BYO -->
  <article class="rounded-2xl border border-violet-900/40 overflow-hidden">
    <div class="border-b border-violet-900/30 bg-violet-950/15 px-5 py-4">
      <span class="pill pill-violet">Camada 5 · BYO no GCP</span>
      <h3 class="mt-2 text-lg font-bold">AlloyDB, BigQuery, Elasticsearch…</h3>
    </div>
    <div class="p-5 text-xs text-slate-400 leading-relaxed space-y-2">
      <ul class="list-disc list-inside space-y-1.5">
        <li><b class="text-violet-300">AlloyDB AI</b> — Postgres + pgvector + índice ScaNN do Google; vetores ao lado de dados operacionais.</li>
        <li><b class="text-violet-300">BigQuery vector search</b> — vetores no warehouse; forte quando o dado já vive no BQ.</li>
        <li><b class="text-violet-300">Spanner / Firestore vectors</b> — quando a distribuição global/documento manda.</li>
        <li><b class="text-violet-300">Grounding com Elasticsearch</b> — reutiliza índice ES existente no Agent Platform (até 10 fontes).</li>
      </ul>
    </div>
  </article>

  <div class="overflow-x-auto rounded-2xl border border-slate-800">
    <table class="w-full text-left text-xs">
      <thead><tr class="border-b border-slate-800 text-slate-500 bg-slate-950/50">
        <th class="px-4 py-3">Preciso de…</th><th class="px-4 py-3">Escolha no Gemini Enterprise</th>
      </tr></thead>
      <tbody class="text-slate-300">
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 text-slate-400">RAG em horas, zero infra</td><td class="px-4 py-3">File Search Store</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 text-slate-400">Busca enterprise + permissões + grounding</td><td class="px-4 py-3">Agent Search / Vertex AI Search</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 text-slate-400">Pipeline managed com VS atrás</td><td class="px-4 py-3">RAG Engine + Vector Search</td></tr>
        <tr class="border-b border-slate-800/70"><td class="px-4 py-3 text-slate-400">Controle de embeddings + escala</td><td class="px-4 py-3">Vertex AI Vector Search (Tree-AH)</td></tr>
        <tr><td class="px-4 py-3 text-slate-400">Vetores ao lado de SQL/analytics</td><td class="px-4 py-3">AlloyDB / BigQuery</td></tr>
      </tbody>
    </table>
  </div>
</section>
"""


def VS8_VS9():
    return r"""
<section id="vs8" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 8</span><span class="pill pill-amber">Comparativo</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Chroma vs Gemini Enterprise — tabela honesta</h2>
  <div class="overflow-x-auto rounded-2xl border border-slate-800">
    <table class="w-full text-left text-xs">
      <thead><tr class="border-b border-slate-800 text-slate-500 bg-slate-950/50">
        <th class="px-3 py-3">Critério</th>
        <th class="px-3 py-3">ChromaDB</th>
        <th class="px-3 py-3">File Search</th>
        <th class="px-3 py-3">Agent Search</th>
        <th class="px-3 py-3">Vertex Vector Search</th>
      </tr></thead>
      <tbody class="text-slate-300">
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 text-slate-400">Soberania</td><td class="px-3 py-2.5">Alta (seu disco/VPC)</td><td class="px-3 py-2.5">Google</td><td class="px-3 py-2.5">Google</td><td class="px-3 py-2.5">Google (seu projeto)</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 text-slate-400">Controle chunk/embed</td><td class="px-3 py-2.5">Total</td><td class="px-3 py-2.5">Mínimo</td><td class="px-3 py-2.5">Baixo</td><td class="px-3 py-2.5">Total (você embeda)</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 text-slate-400">Ops</td><td class="px-3 py-2.5">Baixa–média</td><td class="px-3 py-2.5">Quase zero</td><td class="px-3 py-2.5">Baixa</td><td class="px-3 py-2.5">Média–alta (nós)</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 text-slate-400">Escala confortável</td><td class="px-3 py-2.5">Até ~10⁶–10⁷</td><td class="px-3 py-2.5">Docs de produto</td><td class="px-3 py-2.5">Enterprise search</td><td class="px-3 py-2.5">10⁷–10⁹+</td></tr>
        <tr class="border-b border-slate-800/60"><td class="px-3 py-2.5 text-slate-400">Filtros</td><td class="px-3 py-2.5">where (pós-filtro)</td><td class="px-3 py-2.5">metadata</td><td class="px-3 py-2.5">ACL + search</td><td class="px-3 py-2.5">restricts</td></tr>
        <tr><td class="px-3 py-2.5 text-slate-400">Tempo até 1ª demo</td><td class="px-3 py-2.5">Minutos</td><td class="px-3 py-2.5">Minutos</td><td class="px-3 py-2.5">Horas</td><td class="px-3 py-2.5">Dias (índice+endpoint)</td></tr>
      </tbody>
    </table>
  </div>
  <div class="grid gap-3 sm:grid-cols-2 text-xs">
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-emerald-300">Aula FIAP / lab local</b><div class="mt-1 text-slate-400">Chroma PersistentClient — você vê HNSW, metadata e o bug do pós-filtro com as próprias mãos.</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-blue-300">Assistente no Workspace</b><div class="mt-1 text-slate-400">Agent Search + grounding Gemini — permissões e conectores importam mais que tunar M.</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-amber-300">50M vetores, embed custom</b><div class="mt-1 text-slate-400">Vertex AI Vector Search Tree-AH + STREAM_UPDATE.</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-4"><b class="text-violet-300">Weekend hack / PDF Q&amp;A</b><div class="mt-1 text-slate-400">Gemini File Search Store — zero índice para administrar.</div></div>
  </div>
</section>

<section id="vs9" class="scroll-mt-24 space-y-6">
  <div class="flex items-center gap-3"><span class="pill">Capítulo 9</span><span class="pill pill-emerald">Recap</span></div>
  <h2 class="text-2xl font-bold sm:text-3xl">Recapitulando</h2>
  <div class="relative space-y-0 pl-6 border-l border-slate-700 text-sm">
    <div class="relative pb-6"><div class="absolute -left-[25px] top-1 h-3 w-3 rounded-full bg-blue-400"></div><b class="text-blue-300">Embedding</b><div class="text-slate-400">cria o endereço no mapa</div></div>
    <div class="relative pb-6"><div class="absolute -left-[25px] top-1 h-3 w-3 rounded-full bg-amber-400"></div><b class="text-amber-300">Índice ANN</b><div class="text-slate-400">atalhos para achar vizinhos (HNSW, IVF, Tree-AH…)</div></div>
    <div class="relative pb-6"><div class="absolute -left-[25px] top-1 h-3 w-3 rounded-full bg-emerald-400"></div><b class="text-emerald-300">Vector Store</b><div class="text-slate-400">guarda vetor+doc+metadata e serve a API</div></div>
    <div class="relative"><div class="absolute -left-[25px] top-1 h-3 w-3 rounded-full bg-violet-400"></div><b class="text-violet-300">Retrieval → LLM</b><div class="text-slate-400">trechos vão ao modelo; o que o índice perdeu, ninguém recupera</div></div>
  </div>

  <h3 class="font-semibold">Glossário</h3>
  <div class="grid gap-3 sm:grid-cols-2 text-xs">
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">ANN</b><div class="mt-1 text-slate-400">Approximate Nearest Neighbor</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">HNSW</b><div class="mt-1 text-slate-400">Grafo hierárquico navegável (Chroma default)</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">IVF / PQ</b><div class="mt-1 text-slate-400">Células + compressão</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">Tree-AH</b><div class="mt-1 text-slate-400">Algoritmo ANN do Vertex AI Vector Search</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">Collection</b><div class="mt-1 text-slate-400">Namespace de vetores no Chroma</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">Restrict</b><div class="mt-1 text-slate-400">Filtro nativo no Vector Search</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">File Search Store</b><div class="mt-1 text-slate-400">Vector DB managed da API Gemini</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">Grounding</b><div class="mt-1 text-slate-400">Ancorar a resposta do LLM em fontes</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">Pós-filtro</b><div class="mt-1 text-slate-400">Filtra depois do ANN — risco de k incompleto</div></div>
    <div class="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><b class="text-emerald-300">RAG Engine</b><div class="mt-1 text-slate-400">Pipeline managed Google de retrieval</div></div>
  </div>

  <div class="grid gap-4 md:grid-cols-3">
    <a href="embeddings_do_zero.html" class="card-hover block rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
      <span class="pill pill-accent">Base</span>
      <div class="mt-3 font-bold">Embeddings do Zero</div>
      <p class="mt-2 text-sm text-slate-400">O mapa, o cosseno, o buscador semântico.</p>
    </a>
    <a href="rag_agentic.html#indices" class="card-hover block rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
      <span class="pill pill-amber">Avançado</span>
      <div class="mt-3 font-bold">Masterclass · Índices</div>
      <p class="mt-2 text-sm text-slate-400">Filtros, freshness, código de produção.</p>
    </a>
    <a href="rag_agentic.html#embeddings" class="card-hover block rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
      <span class="pill pill-emerald">Avançado</span>
      <div class="mt-3 font-bold">Masterclass · Embeddings</div>
      <p class="mt-2 text-sm text-slate-400">SPLADE, ColBERT, Matryoshka, quantização.</p>
    </a>
  </div>
</section>

<footer class="border-t border-slate-800 pt-8 text-center text-xs text-slate-600">
  Índices e Vector Stores · complemento de
  <a href="embeddings_do_zero.html" class="text-slate-400 hover:text-blue-300">Embeddings do Zero</a>
  e
  <a href="rag_agentic.html" class="text-slate-400 hover:text-blue-300">Neural Architect</a>
</footer>
</main>
</div>
"""


def SCRIPT():
    return r"""
<script>
const CHAPTERS = [
  {id:'vs1',label:'1 · Por que índice'},
  {id:'vs2',label:'2 · Vector Store'},
  {id:'vs3',label:'3 · Famílias ANN'},
  {id:'vs4',label:'4 · Brinquedo'},
  {id:'vs5',label:'5 · Recall'},
  {id:'vs6',label:'6 · ChromaDB'},
  {id:'vs7',label:'7 · Gemini Enterprise'},
  {id:'vs8',label:'8 · Comparativo'},
  {id:'vs9',label:'9 · Recap'},
];
const nav = document.getElementById('chapterNav');
CHAPTERS.forEach(c=>{
  const a=document.createElement('a');
  a.href='#'+c.id;
  a.className='nav-link rounded-lg border border-transparent px-3 py-2 text-slate-400 hover:text-slate-200 hover:bg-slate-900/60';
  a.textContent=c.label; a.dataset.cap=c.id; nav.appendChild(a);
});
const menuToggle=document.getElementById('menuToggle');
const sidebar=document.getElementById('sidebar');
const overlay=document.getElementById('sidebarOverlay');
menuToggle.addEventListener('click',()=>{sidebar.classList.toggle('-translate-x-full');overlay.classList.toggle('hidden');});
overlay.addEventListener('click',()=>{sidebar.classList.add('-translate-x-full');overlay.classList.add('hidden');});
nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
  if(window.innerWidth<1024){sidebar.classList.add('-translate-x-full');overlay.classList.add('hidden');}
}));
const io=new IntersectionObserver(entries=>{
  entries.forEach(e=>{if(e.isIntersecting)nav.querySelectorAll('a').forEach(a=>a.classList.toggle('active',a.dataset.cap===e.target.id));});
},{rootMargin:'-30% 0px -55% 0px'});
CHAPTERS.forEach(c=>{const el=document.getElementById(c.id);if(el)io.observe(el);});

function dist(a,b){let s=0;for(let i=0;i<a.length;i++)s+=(a[i]-b[i])**2;return Math.sqrt(s);}
function resizeCanvas(canvas){
  const parent=canvas.parentElement; const w=parent.clientWidth;
  const dpr=Math.min(window.devicePixelRatio||1,2);
  const cssH=parseInt(canvas.getAttribute('height'),10)||400;
  canvas.style.width=w+'px'; canvas.style.height=cssH+'px';
  canvas.width=Math.floor(w*dpr); canvas.height=Math.floor(cssH*dpr);
  const ctx=canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
  return {w,h:cssH,ctx};
}

const ann={points:[],cells:3,query:null,mode:'brute',visited:[],found:null,trueNN:null,path:[],graph:[]};
function seededRandom(seed){let s=seed;return()=>{s=(s*16807)%2147483647;return(s-1)/2147483646;};}
function generateAnnPoints(seed=42){
  const rnd=seededRandom(seed); const pts=[];
  for(let i=0;i<900;i++) pts.push({id:i,x:0.05+rnd()*0.9,y:0.05+rnd()*0.9});
  ann.points=pts;
  ann.graph=pts.map((p,i)=>{
    const others=pts.filter(o=>o.id!==p.id).map(o=>({id:o.id,d:dist([p.x,p.y],[o.x,o.y])})).sort((a,b)=>a.d-b.d).slice(0,4).map(o=>o.id);
    for(let k=0;k<2;k++) others.push(Math.floor(rnd()*pts.length));
    return [...new Set(others)];
  });
  ann.visited=[]; ann.found=null; ann.trueNN=null; ann.path=[];
}
function cellOf(p){const c=ann.cells; const cx=Math.min(c-1,Math.floor(p.x*c)); const cy=Math.min(c-1,Math.floor(p.y*c)); return cx+cy*c;}
function trueNearest(q){let best=null,bestD=Infinity; ann.points.forEach(p=>{const d=dist([p.x,p.y],[q.x,q.y]); if(d<bestD){bestD=d;best=p;}}); return best;}
function drawAnn(){
  const canvas=document.getElementById('annCanvas'); const {w,h,ctx}=resizeCanvas(canvas); ctx.clearRect(0,0,w,h);
  if(ann.mode==='ivf'){
    const c=ann.cells;
    for(let i=1;i<c;i++){ctx.strokeStyle='#1e293b';ctx.beginPath();ctx.moveTo((i/c)*w,0);ctx.lineTo((i/c)*w,h);ctx.moveTo(0,(i/c)*h);ctx.lineTo(w,(i/c)*h);ctx.stroke();}
    if(ann.query&&ann.visited.length){
      const probed=new Set(ann.visited.map(id=>cellOf(ann.points[id])));
      probed.forEach(cellId=>{const cx=cellId%c,cy=Math.floor(cellId/c);ctx.fillStyle='rgba(59,130,246,0.08)';ctx.fillRect((cx/c)*w,(cy/c)*h,w/c,h/c);});
    }
  }
  if(ann.mode==='hnsw'){
    ctx.strokeStyle='#1e293b';ctx.lineWidth=0.5;
    ann.points.forEach((p,i)=>{(ann.graph[i]||[]).slice(0,3).forEach(j=>{if(j<=i)return;const o=ann.points[j];if(!o)return;ctx.beginPath();ctx.moveTo(p.x*w,p.y*h);ctx.lineTo(o.x*w,o.y*h);ctx.stroke();});});
    if(ann.path.length>1){ctx.strokeStyle='#fbbf24';ctx.lineWidth=2;ctx.beginPath();ann.path.forEach((id,idx)=>{const p=ann.points[id]; if(idx===0)ctx.moveTo(p.x*w,p.y*h); else ctx.lineTo(p.x*w,p.y*h);});ctx.stroke();}
  }
  const visitedSet=new Set(ann.visited);
  ann.points.forEach(p=>{
    ctx.beginPath(); ctx.arc(p.x*w,p.y*h,visitedSet.has(p.id)?2.5:1.4,0,Math.PI*2);
    if(ann.found&&ann.found.id===p.id){ctx.fillStyle='#34d399';ctx.arc(p.x*w,p.y*h,5,0,Math.PI*2);}
    else if(ann.trueNN&&ann.trueNN.id===p.id) ctx.fillStyle='#f472b6';
    else if(visitedSet.has(p.id)) ctx.fillStyle='#60a5fa';
    else ctx.fillStyle='#334155';
    ctx.fill();
  });
  if(ann.query){
    const qx=ann.query.x*w,qy=ann.query.y*h;
    ctx.fillStyle='#fbbf24'; ctx.beginPath();
    for(let i=0;i<10;i++){const a=(i*Math.PI)/5-Math.PI/2;const r=i%2===0?10:4;const x=qx+Math.cos(a)*r,y=qy+Math.sin(a)*r; if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}
    ctx.closePath();ctx.fill();
  }
}
function runAnnSearch(){
  if(!ann.query){document.getElementById('annExplain').textContent='Primeiro clique no mapa.';return;}
  const q=ann.query; ann.trueNN=trueNearest(q); ann.visited=[]; ann.found=null; ann.path=[];
  let comparisons=0, found=null;
  if(ann.mode==='brute'){
    let bestD=Infinity;
    ann.points.forEach(p=>{comparisons++;ann.visited.push(p.id);const d=dist([p.x,p.y],[q.x,q.y]);if(d<bestD){bestD=d;found=p;}});
    document.getElementById('annExplain').innerHTML="<b class='text-rose-300'>Força bruta:</b> visitamos todas as casas. Sempre certo — explode com milhões.";
    document.getElementById('annStrategy').textContent='Exata';
  } else if(ann.mode==='ivf'){
    const nprobe=+document.getElementById('nprobe').value; const c=ann.cells; const centers=[];
    for(let cy=0;cy<c;cy++) for(let cx=0;cx<c;cx++) centers.push({id:cx+cy*c,x:(cx+.5)/c,y:(cy+.5)/c});
    centers.sort((a,b)=>dist([a.x,a.y],[q.x,q.y])-dist([b.x,b.y],[q.x,q.y]));
    const probe=new Set(centers.slice(0,nprobe).map(x=>x.id)); let bestD=Infinity;
    ann.points.forEach(p=>{if(!probe.has(cellOf(p)))return;comparisons++;ann.visited.push(p.id);const d=dist([p.x,p.y],[q.x,q.y]);if(d<bestD){bestD=d;found=p;}});
    document.getElementById('annExplain').innerHTML=`<b class='text-amber-300'>IVF:</b> ${nprobe}/${c*c} células. Aumente nprobe se errar.`;
    document.getElementById('annStrategy').textContent=`IVF nprobe=${nprobe}`;
  } else {
    let cur=0,entryD=Infinity;
    ann.points.forEach(p=>{const d=dist([p.x,p.y],[.5,.5]);if(d<entryD){entryD=d;cur=p.id;}});
    const visited=new Set(); ann.path=[cur];
    for(let step=0;step<40;step++){
      if(visited.has(cur))break; visited.add(cur); ann.visited.push(cur); comparisons++;
      let best=cur,bestD=dist([ann.points[cur].x,ann.points[cur].y],[q.x,q.y]);
      (ann.graph[cur]||[]).forEach(nid=>{comparisons++; if(!visited.has(nid))ann.visited.push(nid);
        const d=dist([ann.points[nid].x,ann.points[nid].y],[q.x,q.y]); if(d<bestD){bestD=d;best=nid;}});
      if(best===cur)break; cur=best; ann.path.push(cur);
    }
    found=ann.points[cur];
    document.getElementById('annExplain').innerHTML="<b class='text-blue-300'>HNSW:</b> saltos no grafo — avião → ônibus → a pé.";
    document.getElementById('annStrategy').textContent='HNSW greedy';
  }
  ann.found=found;
  const ok=found&&ann.trueNN&&found.id===ann.trueNN.id;
  document.getElementById('annComparisons').textContent=comparisons.toLocaleString('pt-BR');
  document.getElementById('annTime').textContent=(comparisons*0.002).toFixed(2)+' ms';
  const re=document.getElementById('annRecall');
  if(ok){re.textContent='Sim';re.className='mt-1 text-xl font-semibold text-emerald-300';}
  else{re.textContent='Não';re.className='mt-1 text-xl font-semibold text-rose-300';}
  drawAnn();
}
generateAnnPoints(); drawAnn();
document.getElementById('annCanvas').addEventListener('click',e=>{
  const rect=e.target.getBoundingClientRect();
  ann.query={x:(e.clientX-rect.left)/rect.width,y:(e.clientY-rect.top)/rect.height};
  ann.visited=[];ann.found=null;ann.trueNN=null;ann.path=[]; drawAnn();
});
document.querySelectorAll('.ann-mode').forEach(btn=>btn.addEventListener('click',()=>{
  document.querySelectorAll('.ann-mode').forEach(b=>b.classList.remove('active')); btn.classList.add('active');
  ann.mode=btn.dataset.mode;
  document.getElementById('ivfControls').classList.toggle('hidden',ann.mode!=='ivf');
  document.getElementById('ivfControls').classList.toggle('flex',ann.mode==='ivf');
  ann.visited=[];ann.found=null;ann.path=[]; drawAnn();
}));
document.getElementById('nprobe').addEventListener('input',e=>document.getElementById('nprobeVal').textContent=e.target.value);
document.getElementById('annSearchBtn').addEventListener('click',runAnnSearch);
document.getElementById('annResetBtn').addEventListener('click',()=>{generateAnnPoints(Math.floor(Math.random()*10000));ann.query=null;drawAnn();});
window.addEventListener('resize',()=>drawAnn());

new Chart(document.getElementById('annChart'),{
  type:'scatter',
  data:{datasets:[
    {label:'Força bruta',data:[{x:800,y:1}],backgroundColor:'#f43f5e',pointRadius:10},
    {label:'HNSW',data:[{x:2,y:.92},{x:5,y:.97},{x:12,y:.995}],backgroundColor:'#3b82f6',pointRadius:8},
    {label:'IVF-PQ',data:[{x:1.5,y:.85},{x:4,y:.92},{x:10,y:.96}],backgroundColor:'#f59e0b',pointRadius:8},
    {label:'Tree-AH / DiskANN',data:[{x:8,y:.93},{x:20,y:.97}],backgroundColor:'#a78bfa',pointRadius:8},
  ]},
  options:{responsive:true,maintainAspectRatio:false,
    scales:{x:{type:'logarithmic',title:{display:true,text:'Latência relativa (log)',color:'#64748b'},ticks:{color:'#64748b'},grid:{color:'#1e293b'}},
            y:{min:.8,max:1.02,title:{display:true,text:'Recall',color:'#64748b'},ticks:{color:'#64748b'},grid:{color:'#1e293b'}}},
    plugins:{legend:{labels:{color:'#94a3b8',boxWidth:12}}}
  }
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
