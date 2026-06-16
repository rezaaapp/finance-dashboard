from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import BinaryIO

import pdfplumber

from app.imports.models.import_models import ParsedImportResult
from app.imports.parsers.base_parser import BaseParser


class BluPdfParser(BaseParser):
    provider = "blu"

    DATETIME_PATTERN = re.compile(
        r"^(?P<datetime>\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})(?:\s*[-|]\s*|\s+)(?P<body>.+)$"
    )
    SECTION_PATTERN = re.compile(
        r"^(?P<section>bluAccount|bluSpending(?:\s*-\s*.+)?)$",
        re.IGNORECASE,
    )
    AMOUNT_PATTERN = re.compile(
        r"(?P<amount>(?:Rp)?\s*[\d.,]+)(?:\s+|\s*[-|]\s*)(?P<transaction_type>CR|DB|DEBIT|KREDIT|CREDIT)$",
        re.IGNORECASE,
    )

    def parse(self, file: BinaryIO) -> ParsedImportResult:
        file.seek(0)
        lines = self._extract_lines(file)
        transactions = self._parse_lines(lines)

        return ParsedImportResult(
            provider=self.provider,
            transactions=transactions,
        )

    def _extract_lines(self, file: BinaryIO) -> list[str]:
        lines: list[str] = []

        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""

                for raw_line in page_text.splitlines():
                    line = self._normalize_line(raw_line)

                    if not line:
                        continue

                    lines.append(line)

        return lines

    def _parse_lines(self, lines: list[str]) -> list[dict]:
        transactions: list[dict] = []
        active_review_group = ""
        current_block: list[str] = []

        def flush_current_block():
            nonlocal current_block

            if not current_block:
                return

            transaction = self._build_transaction(
                current_block,
                review_group=active_review_group,
            )

            if transaction is not None:
                transactions.append(transaction)

            current_block = []

        for line in lines:
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                flush_current_block()
                active_review_group = self._parse_review_group(section_match.group("section"))
                continue

            if self.DATETIME_PATTERN.match(line):
                flush_current_block()
                current_block = [line]
                continue

            if current_block:
                current_block.append(line)

        flush_current_block()

        return transactions

    def _build_transaction(self, block_lines: list[str], *, review_group: str) -> dict | None:
        first_line = block_lines[0]
        datetime_match = self.DATETIME_PATTERN.match(first_line)

        if not datetime_match:
            return None

        block_text = " ".join(block_lines)
        amount_match = self.AMOUNT_PATTERN.search(block_text)

        if not amount_match:
            return None

        transaction_type = amount_match.group("transaction_type").upper()
        amount = self._parse_amount(amount_match.group("amount"))
        merchant_text = self._extract_merchant_text(
            datetime_match.group("body"),
            block_lines[1:],
            amount_match.group(0),
        )

        return {
            "datetime": datetime_match.group("datetime"),
            "merchant": merchant_text,
            "amount": amount,
            "direction": self._resolve_direction(transaction_type),
            "transaction_type": transaction_type,
            "review_group": review_group,
            "raw_text": " | ".join(block_lines),
        }

    def _extract_merchant_text(
        self,
        first_line_body: str,
        continuation_lines: list[str],
        amount_text: str,
    ) -> str:
        merchant_seed = first_line_body.rsplit(amount_text, 1)[0].strip()
        merchant_parts = [merchant_seed] if merchant_seed else []

        for line in continuation_lines:
            cleaned_line = self._normalize_line(line)

            if cleaned_line:
                merchant_parts.append(self._strip_amount_suffix(cleaned_line))

        return " ".join(part for part in merchant_parts if part).strip()

    def _parse_review_group(self, section_text: str) -> str:
        normalized_section = self._normalize_line(section_text)

        if "-" not in normalized_section:
            return normalized_section

        _, review_group = normalized_section.split("-", 1)
        return review_group.strip()

    def _parse_amount(self, raw_amount: str) -> float:
        normalized_amount = raw_amount.upper().replace("RP", "").replace(" ", "")

        if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", normalized_amount):
            normalized_amount = normalized_amount.replace(".", "").replace(",", ".")
        elif "," in normalized_amount and "." in normalized_amount:
            normalized_amount = normalized_amount.replace(".", "").replace(",", ".")
        elif "," in normalized_amount:
            normalized_amount = normalized_amount.replace(",", ".")

        try:
            return float(Decimal(normalized_amount))
        except InvalidOperation:
            return 0.0

    def _resolve_direction(self, transaction_type: str) -> str:
        if transaction_type in {"CR", "CREDIT", "KREDIT"}:
            return "income"

        return "expense"

    def _strip_amount_suffix(self, value: str) -> str:
        stripped_value = self.AMOUNT_PATTERN.sub("", value).strip()
        return stripped_value or value

    def _normalize_line(self, value: str) -> str:
        return " ".join(value.replace("\xa0", " ").split())
