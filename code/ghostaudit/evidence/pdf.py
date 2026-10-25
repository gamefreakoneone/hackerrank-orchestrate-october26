"""PDF business documents → one Observation per resource id named in the document."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from ghostaudit.evidence.derive import RESOURCE_RE, config, make_observation
from ghostaudit.evidence.model import Observation


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def parse_pdf(file_id: str, captured_at: datetime, text: str) -> list[Observation]:
    title = text.strip().splitlines()[0].strip() if text.strip() else ""
    category = config()["pdf_title_category"].get(title)
    fields = {"title": title, "text": text, "record_type": category}
    return [make_observation(evidence_id=file_id, captured_at=captured_at, source_kind="pdf", container=title,
                             physical_copy="document", resource_id=resource_id, fields=fields)
            for resource_id in sorted(set(RESOURCE_RE.findall(text)))]
