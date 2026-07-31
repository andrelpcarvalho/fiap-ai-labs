"""
Gera o PDF do lab RAG (Conta Premium) em data/lab/lab_conta_premium.pdf.
Uso: python scripts/generate_lab_pdf.py
Requer: pip install fpdf2  ou  pip install -e ".[lab]"
"""

import unicodedata
from pathlib import Path

TITLE = "Conta Premium — Produto Banco (Lab RAG)"

INTRO = (
    "A Conta Premium é um produto voltado a clientes com maior relacionamento "
    "e renda, oferecendo isenções, limites diferenciados e atendimento prioritário."
)

SECTIONS = [
    (
        "Benefícios",
        [
            "Isenção de taxa de manutenção mensal.",
            "TEDs: até 5 gratuitos por mês; após isso, R$ 15,00 por TED.",
            "Saques em rede própria: ilimitados. Saques em rede 24h: R$ 10,00 cada.",
            "Cartão de débito e crédito sem anuidade no primeiro ano; "
            "segunda via a R$ 35,00.",
            "Linha de crédito pré-aprovada e taxas diferenciadas em empréstimo "
            "pessoal (a partir de 0,85% a.m.).",
        ],
    ),
    (
        "Requisitos para adesão",
        [
            "Renda mensal comprovada mínima: R$ 5.000,00.",
            "Manter saldo médio de R$ 10.000,00 ou aplicações equivalentes "
            "no trimestre.",
        ],
    ),
    (
        "Canais de atendimento",
        [
            "App, internet banking, agência e central de relacionamento (telefone).",
            "Proposta de empréstimo pode ser feita pelo agente virtual; "
            "condições sujeitas a análise de crédito.",
        ],
    ),
]

FOOTER_NOTE = "Documento gerado por scripts/generate_lab_pdf.py para o lab RAG ChromaDB."

# Fontes Unicode conhecidas (Windows, Linux, macOS), em ordem de preferência.
FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]


def find_unicode_font() -> tuple[str, str] | None:
    for regular, bold in FONT_CANDIDATES:
        if Path(regular).is_file() and Path(bold).is_file():
            return regular, bold
    return None


def to_ascii(text: str) -> str:
    """Remove acentos para o fallback com fontes core (latin-1 limitado)."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").replace("—", "-")


def main() -> None:
    try:
        from fpdf import FPDF
    except ImportError as e:
        raise SystemExit(
            'fpdf2 não instalado. Rode: pip install fpdf2  ou  pip install -e ".[lab]"'
        ) from e

    out_dir = Path(__file__).resolve().parent.parent / "data" / "lab"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lab_conta_premium.pdf"

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    font_files = find_unicode_font()
    if font_files:
        pdf.add_font("Body", style="", fname=font_files[0])
        pdf.add_font("Body", style="B", fname=font_files[1])
        font = "Body"
        txt = lambda s: s  # noqa: E731
    else:
        # Sem fonte Unicode disponível: usa Helvetica e remove acentos.
        font = "Helvetica"
        txt = to_ascii

    def paragraph(text: str, size: float = 11, style: str = "", indent: float = 0.0) -> None:
        pdf.set_font(font, style=style, size=size)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(0, 6, txt(text), new_x="LMARGIN", new_y="NEXT")

    def bullet(text: str) -> None:
        pdf.set_font(font, size=11)
        start_y = pdf.get_y()
        pdf.set_xy(pdf.l_margin + 2, start_y)
        pdf.cell(5, 6, txt("•") if font_files else "-")
        pdf.set_xy(pdf.l_margin + 7, start_y)
        pdf.multi_cell(0, 6, txt(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # Título
    pdf.set_font(font, style="B", size=16)
    pdf.multi_cell(0, 9, txt(TITLE), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(120, 120, 120)
    pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
    pdf.ln(6)

    paragraph(INTRO)
    pdf.ln(4)

    for heading, items in SECTIONS:
        pdf.set_font(font, style="B", size=12.5)
        pdf.multi_cell(0, 7, txt(heading), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        for item in items:
            bullet(item)
        pdf.ln(3)

    pdf.ln(2)
    pdf.set_text_color(110, 110, 110)
    paragraph(FOOTER_NOTE, size=9)

    pdf.output(str(out_path))
    print(f"PDF gerado: {out_path}")


if __name__ == "__main__":
    main()
