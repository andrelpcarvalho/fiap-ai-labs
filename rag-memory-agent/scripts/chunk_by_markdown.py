import re
from src.indexing.chunking import _chunk_recursive  # fallback reaproveitado, não reimplementado

HEADER_RE = re.compile(r"^(#{1,3})\s+(.*)")

def chunk_by_markdown(text, max_size=512):
    chunks = []
    heading_stack = []  # pilha: [(nivel, titulo), ...] -> "onde estou agora"
    buffer_lines = []

    def flush():
        content = "\n".join(buffer_lines).strip()
        if not content:
            return
        path = " > ".join(h[1] for h in heading_stack)  # ex: "Politicas > Handoff"
        if len(content) <= max_size:
            chunks.append({"text": content, "heading_path": path})
        else:
            # secao grande demais: reaproveita o recursive existente, mas
            # PROPAGA o mesmo heading_path para cada sub-chunk gerado
            for sub in _chunk_recursive(content, max_size):
                chunks.append({"text": sub, "heading_path": path})

    for line in text.splitlines():
        m = HEADER_RE.match(line)
        if m:
            flush()  # fecha a secao anterior antes de trocar de header
            buffer_lines = []
            level = len(m.group(1))  # "#"=1, "##"=2, "###"=3
            title = m.group(2).strip()
            # trunca a pilha: remove tudo de nivel >= ao novo header (evita path acumulado errado)
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, title))
        else:
            buffer_lines.append(line)
    flush()  # fecha a ultima secao do arquivo
    return chunks