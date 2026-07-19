from __future__ import annotations

from hashlib import sha256
from typing import BinaryIO, Callable

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException


class PdfPasswordRequiredError(ValueError):
    error_code = "encrypted_pdf"


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

    try:
        pdf_context = pdfplumber.open(file)
    except PDFPasswordIncorrect as exc:
        raise PdfPasswordRequiredError("PDF requires a password") from exc
    except PdfminerException as exc:
        if any(isinstance(argument, PDFPasswordIncorrect) for argument in exc.args):
            raise PdfPasswordRequiredError("PDF requires a password") from exc
        raise

    with pdf_context as pdf:
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
