"""
Lab — Precisão léxica × Similaridade semântica.
Compara três formas de medir 'parecido' entre textos:
  1. Jaccard (léxico puro): interseção / união dos conjuntos de palavras.
  2. Mock/hash (cosseno de vetores SHA-256): igualdade exata, sem semântica.
  3. Embedding local (cosseno MiniLM multilíngue): similaridade semântica.

Uso:
  python scripts/lab_lexico_vs_semantico.py --apostas   # pares SEM os scores (fase de apostas)
  python scripts/lab_lexico_vs_semantico.py             # tabela completa (gabarito)
  python scripts/lab_lexico_vs_semantico.py --par "frase A" "frase B"
  python scripts/lab_lexico_vs_semantico.py --busca
  python scripts/lab_lexico_vs_semantico.py --busca --query "sua pergunta"
"""

from __future__ import annotations

import argparse
import logging
import re
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

# Neste lab o backend mock é usado DE PROPÓSITO (para mostrar que hash não tem
# semântica); silencia o aviso "Usando embeddings mock" que pollui a tabela.
logging.getLogger("src.indexing.embedding").setLevel(logging.ERROR)

# Pares do duelo: cada um foi escolhido para expor uma diferença entre
# matching léxico e semântico. NÃO altere a ordem (os docs referenciam P1..P6).
PAIRS: list[tuple[str, str, str]] = [
    (
        "P1 paráfrase (mesmo sentido, outras palavras)",
        "Qual a taxa de juros do financiamento de veículos?",
        "Quanto custa o crédito para comprar um carro?",
    ),
    (
        "P2 mesmas palavras, sentido invertido",
        "O cliente recusou a proposta do banco.",
        "O banco recusou a proposta do cliente.",
    ),
    (
        "P3 erro de digitação (1 acento)",
        "emprestimo pessoal com taxa baixa",
        "empréstimo pessoal com taxa baixa",
    ),
    (
        "P4 mesmo vocabulário, pergunta diferente",
        "Como cancelar meu cartão de crédito?",
        "Como aumentar o limite do meu cartão de crédito?",
    ),
    (
        "P5 idiomas diferentes, mesmo sentido",
        "Quero financiar um carro novo.",
        "I want to finance a new car.",
    ),
    (
        "P6 sem relação nenhuma",
        "Quais são as tarifas da conta premium?",
        "O estacionamento do shopping fecha às 22 horas.",
    ),
]

# Mini-corpus da busca: 6 'fatos' de banco (estilo data/lab).
CORPUS = [
    "Clientes com relacionamento acima de 5 anos têm desconto na taxa do empréstimo pessoal.",
    "A anuidade do cartão de crédito premium é isenta no primeiro ano.",
    "O limite do cheque especial é definido conforme análise de crédito.",
    "Transferências via PIX são gratuitas e ilimitadas para pessoa física.",
    "O financiamento de veículos exige entrada mínima de 20% do valor do bem.",
    "A conta premium dá acesso a salas VIP em aeroportos nacionais.",
]

DEFAULT_QUERY = "Pago menos juros se já for cliente antigo do banco?"


def tokenize(text: str) -> set[str]:
    """Minúsculas, sem pontuação; mantém acentos (é assim que léxico 'puro' falha)."""
    text = text.lower()
    return set(re.findall(r"\w+", text, flags=re.UNICODE))


def jaccard(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def score_pair(a: str, b: str) -> tuple[float, float, float]:
    """Retorna (jaccard, cos_mock, cos_semantico) para o par."""
    lex = jaccard(a, b)
    [ma, mb] = embed_texts([a, b], backend="mock")
    [sa, sb] = embed_texts([a, b], backend="local")
    return lex, cosine_similarity(ma, mb), cosine_similarity(sa, sb)


def print_pairs(with_scores: bool) -> None:
    if with_scores:
        print(f"\n{'par':<46} {'léxico':>7} {'hash':>7} {'semânt.':>8}")
        print("-" * 72)
    for label, a, b in PAIRS:
        if with_scores:
            lex, hsh, sem = score_pair(a, b)
            print(f"{label:<46} {lex:>7.2f} {hsh:>7.2f} {sem:>8.2f}")
            print(f'    A: "{a}"')
            print(f'    B: "{b}"')
        else:
            print(f"\n{label}")
            print(f'  A: "{a}"')
            print(f'  B: "{b}"')
    if with_scores:
        print("-" * 72)
        print(
            "léxico  = Jaccard (palavras em comum / palavras totais), 0 a 1\n"
            "hash    = cosseno dos embeddings mock (SHA-256) — igualdade exata\n"
            "semânt. = cosseno dos embeddings locais (MiniLM multilíngue)"
        )
    else:
        print(
            "\nAposte em grupo, para CADA par: o score léxico será ALTO ou BAIXO?"
            "\nE o semântico? Anotem antes de rodar sem --apostas."
        )


def custom_pair(a: str, b: str) -> None:
    lex, hsh, sem = score_pair(a, b)
    print(f'\nA: "{a}"')
    print(f'B: "{b}"')
    print(f"\nléxico (Jaccard)      : {lex:.4f}")
    print(f"hash (mock, cosseno)  : {hsh:.4f}")
    print(f"semântico (cosseno)   : {sem:.4f}")


def search(query: str) -> None:
    """Ranqueia o mini-corpus pela visão léxica e pela semântica, lado a lado."""
    sem_vecs = embed_texts([query] + CORPUS, backend="local")
    q_vec, doc_vecs = sem_vecs[0], sem_vecs[1:]

    lex_scores = [(jaccard(query, doc), doc) for doc in CORPUS]
    sem_scores = [
        (cosine_similarity(q_vec, dv), doc) for dv, doc in zip(doc_vecs, CORPUS)
    ]
    lex_rank = sorted(lex_scores, key=lambda x: -x[0])
    sem_rank = sorted(sem_scores, key=lambda x: -x[0])

    print(f'\nPergunta: "{query}"')
    print("\n--- Ranking LÉXICO (Jaccard) ---")
    for i, (score, doc) in enumerate(lex_rank, 1):
        print(f"  {i}. [{score:.2f}] {doc}")
    print("\n--- Ranking SEMÂNTICO (embedding local) ---")
    for i, (score, doc) in enumerate(sem_rank, 1):
        print(f"  {i}. [{score:.2f}] {doc}")

    lex_top = lex_rank[0][1]
    sem_top = sem_rank[0][1]
    print("\nTop-1 léxico    :", lex_top[:70] + ("..." if len(lex_top) > 70 else ""))
    print("Top-1 semântico :", sem_top[:70] + ("..." if len(sem_top) > 70 else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Léxico × semântico (Lab de similaridade)")
    parser.add_argument("--apostas", action="store_true", help="Mostra os pares SEM scores")
    parser.add_argument("--par", nargs=2, metavar=("A", "B"), help="Compara um par customizado")
    parser.add_argument("--busca", action="store_true", help="Mini-busca: ranking léxico × semântico")
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY, help="Pergunta da busca")
    args = parser.parse_args()

    if args.par:
        custom_pair(args.par[0], args.par[1])
    elif args.busca:
        search(args.query)
    else:
        print_pairs(with_scores=not args.apostas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
