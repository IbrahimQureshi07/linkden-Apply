from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _pdf_text(data)
    if suffix in {".docx", ".doc"}:
        if suffix == ".doc":
            raise ValueError("Legacy .doc files are not supported; please save as .docx or PDF.")
        return _docx_text(data)
    if suffix in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX, or TXT.")


def extract_text_from_path(path: Path) -> str:
    return extract_text_from_bytes(path.read_bytes(), path.name)


def _pdf_text(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _docx_text(data: bytes) -> str:
    doc = Document(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
