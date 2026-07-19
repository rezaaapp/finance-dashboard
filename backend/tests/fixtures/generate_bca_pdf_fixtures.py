from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


FIXTURE_ROOT = Path(__file__).resolve().parent
STATEMENT_TEXT_PATH = FIXTURE_ROOT / "bca_statement_synthetic.txt"


def build_pdf(pages: list[list[str]]) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    for page_lines in pages:
        y_position = A4[1] - 48
        pdf.setFont("Helvetica", 8)
        for line in page_lines:
            pdf.drawString(36, y_position, line)
            y_position -= 12
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def encrypt_pdf(pdf_bytes: bytes, *, user_password: str) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.encrypt(user_password=user_password, owner_password="owner-synthetic")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def main():
    statement_lines = STATEMENT_TEXT_PATH.read_text(encoding="utf-8").splitlines()
    split_index = statement_lines.index("REKENING TAHAPAN XPRESI", 1)
    statement_pdf = build_pdf([
        statement_lines[:split_index],
        statement_lines[split_index:],
    ])
    marker_pdf = build_pdf([["REKENING TAHAPAN XPRESI", "DATA SINTETIS"]])
    scan_only_pdf = build_pdf([[]])

    (FIXTURE_ROOT / "bca_statement_synthetic.pdf").write_bytes(statement_pdf)
    (FIXTURE_ROOT / "bca_permission_encrypted_synthetic.pdf").write_bytes(
        encrypt_pdf(marker_pdf, user_password="")
    )
    (FIXTURE_ROOT / "bca_password_required_synthetic.pdf").write_bytes(
        encrypt_pdf(marker_pdf, user_password="synthetic-password")
    )
    (FIXTURE_ROOT / "bca_scan_only_synthetic.pdf").write_bytes(scan_only_pdf)


if __name__ == "__main__":
    main()
