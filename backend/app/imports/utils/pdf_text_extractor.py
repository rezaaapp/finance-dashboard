from __future__ import annotations

from hashlib import sha256
from typing import BinaryIO, Callable

import pdfplumber


def normalize_pdf_text_line(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def extract_pdf_metadata(
    file: BinaryIO,
    *,
    line_normalizer: Callable[[str], str] = normalize_pdf_text_line,
) -> dict:
    file.seek(0)
    lines: list[str] = []
    extracted_text = ""

    with pdfplumber.open(file) as pdf:
        page_count = len(pdf.pages)

        for page in pdf.pages:
            page_text = page.extract_text() or ""
            extracted_text += page_text + "\n"

            for raw_line in page_text.splitlines():
                line = line_normalizer(raw_line)

                if line:
                    lines.append(line)

    return {
        "lines": lines,
        "page_count": page_count,
        "extracted_text": extracted_text,
        "extracted_text_length": len(extracted_text.strip()),
        "extracted_text_hash": sha256(extracted_text.encode("utf-8")).hexdigest(),
    }
