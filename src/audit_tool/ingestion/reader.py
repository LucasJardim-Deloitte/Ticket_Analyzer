"""
Camada de ingestão — transforma um ficheiro (qualquer formato) numa lista de
"documentos de ticket" em texto bruto, prontos para a extração.

Um ADAPTADOR por FORMATO FÍSICO (não por cliente). O que varia por cliente/origem é
tratado nos profiles, não aqui.

Suporta:
- 1 ficheiro = 1 ticket (default)
- 1 ficheiro = N tickets (via separador configurável — útil para exports agregados)

Formatos v0.3: .txt, .eml, .pdf (texto selecionável — sem OCR).
"""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path


DEFAULT_TICKET_SEPARATOR = "\n---TICKET---\n"

# Tipos suportados — usados pela UI para o file_uploader
SUPPORTED_EXTENSIONS = ["txt", "eml", "pdf"]


@dataclass
class RawTicketDocument:
    """Um documento de ticket em bruto, pronto para extração."""

    source_file: str
    text: str
    ticket_index: int = 0


def read_file(
    path: Path,
    ticket_separator: str | None = DEFAULT_TICKET_SEPARATOR,
) -> list[RawTicketDocument]:
    """
    Lê um ficheiro e devolve um ou mais RawTicketDocument.
    Delega no adaptador certo pela extensão.
    Extensões desconhecidas caem no leitor de texto (defensivo).
    """
    ext = path.suffix.lower()
    if ext == ".eml":
        text = _read_eml(path)
    elif ext == ".pdf":
        text = _read_pdf(path)
    else:
        text = _read_text(path)

    return _split_into_tickets(text, source_file=path.name, separator=ticket_separator)


# ---------------------------------------------------------------------------
# Adaptadores
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    """Adaptador .txt — tolerante a encoding."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    """
    Adaptador .pdf — extrai texto selecionável página a página com pdfplumber.

    Preserva a estrutura visual (espaços e quebras de linha) para que os rótulos
    dos campos fiquem próximos dos seus valores, facilitando a extração pelo LLM.

    Não suporta PDFs digitalizados (imagem) — esses precisariam de OCR.
    Quando o texto extraído é vazio (PDF de imagem), devolve uma mensagem clara
    para o utilizador ver no drill-down em vez de um campo silenciosamente vazio.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber não está instalado. Corre: pip install pdfplumber"
        )

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            # extract_text com layout=True preserva posição dos elementos
            page_text = page.extract_text(layout=True) or ""
            if page_text.strip():
                pages.append(f"[Página {i}]\n{page_text}")

    text = "\n\n".join(pages).strip()

    if not text:
        return (
            "[AVISO: Não foi possível extrair texto deste PDF. "
            "O ficheiro pode ser um PDF digitalizado (imagem) que requer OCR. "
            "Converte o PDF para texto ou usa um ficheiro .txt como alternativa.]"
        )

    return text


def _read_eml(path: Path) -> str:
    """Adaptador .eml — extrai cabeçalhos relevantes + corpo em texto."""
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    headers = []
    for h in ("From", "To", "Cc", "Subject", "Date"):
        val = msg.get(h)
        if val:
            headers.append(f"{h}: {val}")

    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body_parts.append(part.get_content())
                except Exception:  # noqa: BLE001
                    continue
    else:
        try:
            body_parts.append(msg.get_content())
        except Exception:  # noqa: BLE001
            pass

    return "\n".join(headers) + "\n\n" + "\n".join(body_parts)


# ---------------------------------------------------------------------------
# Suporte a N tickets por ficheiro
# ---------------------------------------------------------------------------

def _split_into_tickets(
    text: str,
    source_file: str,
    separator: str | None,
) -> list[RawTicketDocument]:
    if separator and separator in text:
        chunks = [c.strip() for c in text.split(separator) if c.strip()]
        return [
            RawTicketDocument(source_file=source_file, text=chunk, ticket_index=i)
            for i, chunk in enumerate(chunks)
        ]
    return [RawTicketDocument(source_file=source_file, text=text.strip(), ticket_index=0)]
