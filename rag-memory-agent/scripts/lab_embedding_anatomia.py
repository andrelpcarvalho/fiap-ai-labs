"""
Lab — Anatomia do Embedding (dimensões).
Inspeciona vetores de embedding: dimensão, valores, norma, determinismo
e quanto cada dimensão contribui para separar textos parecidos de diferentes.

Uso:
  python scripts/lab_embedding_anatomia.py
  python scripts/lab_embedding_anatomia.py --text "Sua frase aqui"
  python scripts/lab_embedding_anatomia.py --backend mock
  python scripts/lab_embedding_anatomia.py --compare-backends
  python scripts/lab_embedding_anatomia.py --determinismo
  python scripts/lab_embedding_anatomia.py --dims-progressivas
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# Consoles Windows (cp1252/cp850) podem quebrar com acentos; força UTF-8 com fallback.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.indexing.embedding import cosine_similarity, embed_texts

DEFAULT_TEXT = "O empréstimo pessoal tem taxa a partir de 1,2% ao mês."

# Pares relacionados (paráfrases: mesmo sentido, palavras diferentes) usados
# no experimento --dims-progressivas.
RELATED_PAIRS = [
    (
        "Qual a taxa de juros do empréstimo pessoal?",
        "Quanto custa pegar dinheiro emprestado no banco?",
    ),
    (
        "Como faço para cancelar meu cartão de crédito?",
        "Quero encerrar o cartão, qual o procedimento?",
    ),
    (
        "O financiamento do carro exige entrada?",
        "Preciso dar um valor inicial para financiar o veículo?",
    ),
    (
        "Quais documentos preciso para abrir uma conta?",
        "O que é exigido na abertura de conta corrente?",
    ),
    (
        "O aplicativo do banco está fora do ar?",
        "Não consigo acessar o app, o sistema caiu?",
    ),
]

# Frases de assuntos completamente diferentes entre si. Todos os pares
# possíveis entre elas (10 frases = 45 pares) são "sem relação" — é aqui que
# medimos colisões acidentais em baixa dimensão.
DIVERSE_SENTENCES = [
    "O estacionamento do shopping fecha às 22 horas.",
    "A previsão é de chuva forte no fim de semana.",
    "O restaurante serve almoço até as 15 horas.",
    "A vacina contra a gripe já está disponível nos postos.",
    "O time venceu o campeonato estadual de vôlei.",
    "A receita do bolo leva três ovos e fermento.",
    "O voo para Recife foi remarcado para terça-feira.",
    "A peça de teatro estreia no próximo mês.",
    "O professor adiou a prova de matemática.",
    "A bateria do celular dura menos no frio.",
]


def norm(vector: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def show_vector(text: str, backend: str, n_preview: int = 12) -> None:
    """Mostra a 'cara' do embedding: dimensão, primeiros valores e norma."""
    [vec] = embed_texts([text], backend=backend)
    print(f'\nTexto     : "{text}"')
    print(f"Backend   : {backend}")
    print(f"Dimensões : {len(vec)}")
    preview = ", ".join(f"{v:+.4f}" for v in vec[:n_preview])
    print(f"Primeiros {n_preview} valores:\n  [{preview}, ...]")
    print(f"Norma (comprimento do vetor): {norm(vec):.4f}")
    print(f"Maior valor: {max(vec):+.4f}   Menor valor: {min(vec):+.4f}")


def compare_backends(text: str) -> None:
    """Mesmo texto em backends diferentes: dimensões e normas não batem."""
    print(f'\nTexto: "{text}"')
    print(f"\n{'backend':<8} {'dims':>5} {'norma':>7}  primeiros 4 valores")
    print("-" * 70)
    vectors = {}
    for backend in ("local", "mock"):
        [vec] = embed_texts([text], backend=backend)
        vectors[backend] = vec
        head = ", ".join(f"{v:+.3f}" for v in vec[:4])
        print(f"{backend:<8} {len(vec):>5} {norm(vec):>7.3f}  [{head}, ...]")
    print("-" * 70)
    sim = cosine_similarity(vectors["local"], vectors["mock"])
    print(
        f"Similaridade cosseno entre os dois vetores: {sim:.4f}\n"
        "(dimensões diferentes não são comparáveis — a função retorna 0.0.\n"
        " No ChromaDB, misturar backends gera erro de dimensão na collection.)"
    )


def determinism(text: str, backend: str) -> None:
    """Mesmo texto duas vezes, e o efeito de uma edição de 1 caractere."""
    edited = text.replace(",", ".", 1) if "," in text else text + "."
    [v1] = embed_texts([text], backend=backend)
    [v2] = embed_texts([text], backend=backend)
    [v3] = embed_texts([edited], backend=backend)

    print(f'\nBackend: {backend}')
    print(f'A) "{text}"')
    print(f'B) "{text}"  (idêntico ao A)')
    print(f'C) "{edited}"  (1 caractere alterado)')
    print(f"\ncos(A, B) = {cosine_similarity(v1, v2):.4f}   <- mesmo texto")
    print(f"cos(A, C) = {cosine_similarity(v1, v3):.4f}   <- 1 caractere de diferença")


def progressive_dims(backend: str) -> None:
    """
    Similaridade usando só as primeiras k dimensões do vetor.
    Compara paráfrases (deveriam ficar ALTAS) com 45 pares de frases sem
    relação (deveriam ficar BAIXAS). Em poucas dimensões, pares sem relação
    'colidem' por acaso — a pior colisão invade a zona das paráfrases.
    """
    related = [embed_texts(list(p), backend=backend) for p in RELATED_PAIRS]
    diverse = embed_texts(DIVERSE_SENTENCES, backend=backend)
    total = len(diverse[0])
    n_unrel_pairs = len(DIVERSE_SENTENCES) * (len(DIVERSE_SENTENCES) - 1) // 2

    print(f"\nParáfrases (pares relacionados): {len(RELATED_PAIRS)} pares")
    print(
        f"Frases de assuntos diferentes: {len(DIVERSE_SENTENCES)} frases "
        f"= {n_unrel_pairs} pares sem relação"
    )

    header = (
        f"{'dims':>5} {'paráfrase (média)':>18} {'paráfrase (pior)':>17} "
        f"{'s/ relação (média)':>19} {'s/ relação (pior)':>18} {'margem':>8}"
    )
    print("\n" + header)
    print("-" * len(header))
    ks = [2, 4, 8, 16, 32, 64, 128, total]
    for k in ks:
        rel_sims = [cosine_similarity(a[:k], b[:k]) for a, b in related]
        unrel_sims = [
            cosine_similarity(diverse[i][:k], diverse[j][:k])
            for i in range(len(diverse))
            for j in range(i + 1, len(diverse))
        ]
        rel_mean = sum(rel_sims) / len(rel_sims)
        rel_worst = min(rel_sims)
        unrel_mean = sum(unrel_sims) / len(unrel_sims)
        unrel_worst = max(unrel_sims)  # pior colisão: par sem relação mais "parecido"
        margin = rel_worst - unrel_worst
        print(
            f"{k:>5} {rel_mean:>18.3f} {rel_worst:>17.3f} "
            f"{unrel_mean:>19.3f} {unrel_worst:>18.3f} {margin:>+8.3f}"
        )
    print("-" * len(header))
    print(
        "paráfrase (pior)  = a paráfrase MENOS parecida (deveria continuar alta).\n"
        "s/ relação (pior) = a COLISÃO acidental mais forte entre frases sem relação.\n"
        "margem = paráfrase(pior) - s/relação(pior). Se for NEGATIVA, existe um par\n"
        "sem relação que parece MAIS similar que uma paráfrase real -> a busca erra."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Anatomia do embedding (Lab de dimensões)")
    parser.add_argument("--text", type=str, default=DEFAULT_TEXT, help="Texto a inspecionar")
    parser.add_argument(
        "--backend",
        choices=("local", "mock"),
        default="local",
        help="local = sentence-transformers (semântico); mock = hash SHA-256 (sem semântica)",
    )
    parser.add_argument("--compare-backends", action="store_true", help="Compara local × mock")
    parser.add_argument(
        "--determinismo",
        action="store_true",
        help="Mesmo texto 2x + edição de 1 caractere",
    )
    parser.add_argument(
        "--dims-progressivas",
        action="store_true",
        help="Similaridade usando só as primeiras k dimensões",
    )
    args = parser.parse_args()

    if args.compare_backends:
        compare_backends(args.text)
    elif args.determinismo:
        determinism(args.text, args.backend)
    elif args.dims_progressivas:
        progressive_dims(args.backend)
    else:
        show_vector(args.text, args.backend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
