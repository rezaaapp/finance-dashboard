from __future__ import annotations

import re
from hashlib import sha256
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
    DATE_PATTERN = re.compile(
        r"^(?P<day>\d{2})\s+(?P<month>Jan|Feb|Mar|Apr|Mei|May|Jun|Jul|Agu|Aug|Sep|Okt|Oct|Nov|Des|Dec)\s+(?P<year>\d{4})$",
        re.IGNORECASE,
    )
    DATE_TRANSACTION_PATTERN = re.compile(
        r"^(?P<day>\d{2})\s+(?P<month>Jan|Feb|Mar|Apr|Mei|May|Jun|Jul|Agu|Aug|Sep|Okt|Oct|Nov|Des|Dec)\s+(?P<year>\d{4})\s+(?P<transaction_type>.+)$",
        re.IGNORECASE,
    )
    TIME_PATTERN = re.compile(
        r"^(?P<time>\d{2}:\d{2})\s+(?P<body>.+)$"
    )
    TIME_ONLY_PATTERN = re.compile(r"^(?P<time>\d{2}:\d{2})$")
    SECTION_PATTERN = re.compile(
        r"^(?P<section>bluAccount(?:\s*-\s*.+)?|bluSpending(?:\s*-\s*.+)?)$",
        re.IGNORECASE,
    )
    AMOUNT_PATTERN = re.compile(
        r"(?P<amount>(?:Rp)?\s*[\d.,]+)(?:\s+|\s*[-|]\s*)(?P<transaction_type>CR|DB|DEBIT|KREDIT|CREDIT)$",
        re.IGNORECASE,
    )
    STATEMENT_AMOUNT_PATTERN = re.compile(
        r"^(?P<transaction_type>.+?)\s+(?P<sign>-)?\s*(?P<amount>\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s+(?P<balance>\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)$",
        re.IGNORECASE,
    )
    STATEMENT_AMOUNT_ONLY_PATTERN = re.compile(
        r"^(?P<sign>-)?\s*(?P<amount>\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s+(?P<balance>\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)$",
        re.IGNORECASE,
    )
    SUMMARY_PATTERN = re.compile(
        r"^(Total\s+(?:Pemasukan|Income|Pengeluaran|Expense)|Saldo\s+(?:Awal|Akhir)|Initial\s+Balance|Ending\s+Balance|Disclaimer|BCA\s+Digital)",
        re.IGNORECASE,
    )
    HEADER_PATTERN = re.compile(
        r"^(Tanggal\s*&\s*Jam|Date\s*&\s*Time|Detail\s+Transaksi|Keterangan\s*/\s*Remarks)",
        re.IGNORECASE,
    )
    MONTHS = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "mei": "05",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "agu": "08",
        "aug": "08",
        "sep": "09",
        "okt": "10",
        "oct": "10",
        "nov": "11",
        "des": "12",
        "dec": "12",
    }

    def parse(self, file: BinaryIO) -> ParsedImportResult:
        extraction = self.extract_pdf_metadata(file)
        return self.parse_extracted_lines(
            extraction["lines"],
            page_count=extraction["page_count"],
            extracted_text_length=extraction["extracted_text_length"],
        )

    def parse_extracted_lines(
        self,
        lines: list[str],
        *,
        page_count: int = 0,
        extracted_text_length: int = 0,
    ) -> ParsedImportResult:
        transactions = self._parse_lines(lines)
        return ParsedImportResult(
            provider=self.provider,
            transactions=transactions,
            page_count=page_count,
            extracted_text_length=extracted_text_length,
        )

    def extract_pdf_metadata(self, file: BinaryIO) -> dict:
        file.seek(0)
        lines: list[str] = []
        extracted_text = ""
        page_count = 0

        with pdfplumber.open(file) as pdf:
            page_count = len(pdf.pages)

            for page in pdf.pages:
                page_text = page.extract_text() or ""
                extracted_text += page_text + "\n"

                for raw_line in page_text.splitlines():
                    line = self._normalize_line(raw_line)

                    if not line:
                        continue

                    lines.append(line)

        return {
            "lines": lines,
            "page_count": page_count,
            "extracted_text": extracted_text,
            "extracted_text_length": len(extracted_text.strip()),
            "extracted_text_hash": sha256(extracted_text.encode("utf-8")).hexdigest(),
        }

    def _parse_lines(self, lines: list[str]) -> list[dict]:
        transactions: list[dict] = []
        active_review_group = ""
        current_block: list[str] = []
        active_statement_date = ""

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
                active_statement_date = ""
                continue

            if self._is_ignored_line(line):
                flush_current_block()
                active_statement_date = ""
                continue

            date_transaction_match = self.DATE_TRANSACTION_PATTERN.match(line)
            if date_transaction_match:
                flush_current_block()
                current_block = [line]
                active_statement_date = ""
                continue

            date_match = self.DATE_PATTERN.match(line)
            if date_match:
                flush_current_block()
                active_statement_date = self._normalize_statement_date(date_match)
                continue

            if self.DATETIME_PATTERN.match(line):
                flush_current_block()
                current_block = [line]
                active_statement_date = ""
                continue

            time_match = self.TIME_PATTERN.match(line)
            if time_match and active_statement_date:
                flush_current_block()
                current_block = [
                    f"{active_statement_date} {time_match.group('time')} {time_match.group('body')}"
                ]
                continue

            if current_block:
                current_block.append(line)

        flush_current_block()

        return transactions

    def _build_transaction(self, block_lines: list[str], *, review_group: str) -> dict | None:
        first_line = block_lines[0]
        datetime_match = self.DATETIME_PATTERN.match(first_line)

        if datetime_match:
            return self._build_datetime_transaction(block_lines, datetime_match, review_group=review_group)

        date_transaction_match = self.DATE_TRANSACTION_PATTERN.match(first_line)

        if date_transaction_match:
            return self._build_statement_transaction(
                block_lines,
                date_transaction_match,
                review_group=review_group,
            )

        return None

    def _build_datetime_transaction(
        self,
        block_lines: list[str],
        datetime_match: re.Match,
        *,
        review_group: str,
    ) -> dict | None:
        block_text = " ".join(block_lines)
        amount_fields = self._extract_amount_fields(block_text, block_lines)

        if not amount_fields:
            return None

        transaction_type = amount_fields["transaction_type"]
        amount = self._parse_amount(amount_fields["amount"])
        merchant_text = self._extract_merchant_text(
            datetime_match.group("body"),
            block_lines[1:],
            amount_fields["amount_text"],
        )

        return {
            "datetime": datetime_match.group("datetime"),
            "merchant_original": merchant_text,
            "amount": amount,
            "direction": self._resolve_direction(
                transaction_type,
                is_signed_expense=amount_fields["is_signed_expense"],
                is_statement_format=amount_fields["is_statement_format"],
            ),
            "transaction_type": transaction_type,
            "review_group": review_group,
            "raw_text": " | ".join(block_lines),
        }

    def _build_statement_transaction(
        self,
        block_lines: list[str],
        date_transaction_match: re.Match,
        *,
        review_group: str,
    ) -> dict | None:
        amount_fields = self._extract_amount_fields(" ".join(block_lines), block_lines)

        if not amount_fields:
            return None

        time_line_index = self._find_time_line_index(block_lines)

        if time_line_index is None:
            return None

        transaction_type = date_transaction_match.group("transaction_type").strip()
        statement_date = self._normalize_statement_date(date_transaction_match)
        statement_time = self.TIME_ONLY_PATTERN.match(block_lines[time_line_index]).group("time")
        amount = self._parse_amount(amount_fields["amount"])
        merchant_text = " ".join(
            self._strip_amount_suffix(self._normalize_line(line))
            for line in block_lines[time_line_index + 1:]
            if self._strip_amount_suffix(self._normalize_line(line))
        ).strip()

        return {
            "datetime": f"{statement_date} {statement_time}",
            "merchant_original": merchant_text,
            "amount": amount,
            "direction": self._resolve_direction(
                transaction_type,
                is_signed_expense=amount_fields["is_signed_expense"],
                is_statement_format=amount_fields["is_statement_format"],
            ),
            "transaction_type": transaction_type,
            "review_group": review_group,
            "raw_text": " | ".join(block_lines),
        }

    def _extract_amount_fields(self, block_text: str, block_lines: list[str]) -> dict | None:
        legacy_match = self.AMOUNT_PATTERN.search(block_text)

        if legacy_match:
            transaction_type = legacy_match.group("transaction_type").upper()

            return {
                "amount": legacy_match.group("amount"),
                "amount_text": legacy_match.group(0),
                "transaction_type": transaction_type,
                "is_signed_expense": False,
                "is_statement_format": False,
            }

        for line in reversed(block_lines):
            amount_only_match = self.STATEMENT_AMOUNT_ONLY_PATTERN.match(line)

            if amount_only_match:
                return {
                    "amount": amount_only_match.group("amount"),
                    "amount_text": amount_only_match.group(0),
                    "transaction_type": "",
                    "is_signed_expense": bool(amount_only_match.group("sign")),
                    "is_statement_format": True,
                }

            statement_match = self.STATEMENT_AMOUNT_PATTERN.match(line)

            if not statement_match:
                continue

            transaction_type = statement_match.group("transaction_type").strip()

            if self.SUMMARY_PATTERN.match(transaction_type):
                return None

            return {
                "amount": statement_match.group("amount"),
                "amount_text": statement_match.group(0),
                "transaction_type": transaction_type,
                "is_signed_expense": bool(statement_match.group("sign")),
                "is_statement_format": True,
            }

        return None

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
                stripped_line = self._strip_amount_suffix(cleaned_line)

                if stripped_line != cleaned_line:
                    continue

                merchant_parts.append(stripped_line)

        return " ".join(part for part in merchant_parts if part).strip()

    def _parse_review_group(self, section_text: str) -> str:
        normalized_section = self._normalize_line(section_text)

        if "-" not in normalized_section:
            return normalized_section

        section_name, review_group = normalized_section.split("-", 1)
        if section_name.strip().lower() == "bluaccount":
            return "bluAccount"

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

    def _resolve_direction(
        self,
        transaction_type: str,
        *,
        is_signed_expense: bool = False,
        is_statement_format: bool = False,
    ) -> str:
        if is_signed_expense:
            return "expense"

        if is_statement_format:
            return "income"

        if transaction_type in {"CR", "CREDIT", "KREDIT"}:
            return "income"

        return "expense"

    def _strip_amount_suffix(self, value: str) -> str:
        stripped_value = self.AMOUNT_PATTERN.sub("", value).strip()
        stripped_value = self.STATEMENT_AMOUNT_PATTERN.sub("", stripped_value).strip()
        stripped_value = self.STATEMENT_AMOUNT_ONLY_PATTERN.sub("", stripped_value).strip()
        return stripped_value

    def _normalize_statement_date(self, date_match: re.Match) -> str:
        month = self.MONTHS[date_match.group("month").lower()]
        return f"{date_match.group('day')}/{month}/{date_match.group('year')}"

    def _is_ignored_line(self, line: str) -> bool:
        return bool(self.SUMMARY_PATTERN.match(line) or self.HEADER_PATTERN.match(line))

    def _find_time_line_index(self, block_lines: list[str]) -> int | None:
        for index, line in enumerate(block_lines):
            if self.TIME_ONLY_PATTERN.match(line):
                return index

        return None

    def _normalize_line(self, value: str) -> str:
        return " ".join(value.replace("\xa0", " ").split())
