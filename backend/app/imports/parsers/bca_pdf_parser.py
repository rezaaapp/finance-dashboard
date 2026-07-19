from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, BinaryIO

from pydantic import Field

from app.imports.models.import_models import ImportSectionCandidate, ParsedImportResult
from app.imports.parsers.base_parser import (
    BaseParser,
    InvalidSectionSelectionError,
    MalformedTransactionRowError,
    NoParseableTransactionsError,
    SectionSelectionRequiredError,
    UnsupportedStatementError,
)
from app.imports.utils.fingerprint import build_bca_signature_key
from app.imports.utils.pdf_text_extractor import extract_pdf_metadata


class BcaParsedImportResult(ParsedImportResult):
    statement_empty: bool = False
    warnings: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    section_candidates: list[ImportSectionCandidate] = Field(default_factory=list)
    selected_section: ImportSectionCandidate | None = None
    is_multi_account: bool = False


@dataclass(frozen=True, slots=True)
class BcaStatementSection:
    candidate: ImportSectionCandidate
    lines: tuple[str, ...]
    account_identity_hash: str
    section_identity_hash: str


@dataclass(frozen=True, slots=True)
class BcaSectionDiscovery:
    sections: tuple[BcaStatementSection, ...]

    @property
    def candidates(self) -> list[ImportSectionCandidate]:
        return [section.candidate for section in self.sections]


class BcaPdfParser(BaseParser):
    provider = "bca"

    PROVIDER_METADATA = {
        "_import_provider": "bca",
        "source_fund": "BCA",
        "source_origin": "bca_pdf",
    }
    REVIEW_GROUP = ""

    ACCOUNT_PATTERN = re.compile(
        r"\bNO\.?\s*REKENING\s*:?\s*(?P<account>(?:\d[\s-]?){6,20})",
        re.IGNORECASE,
    )
    PERIOD_PATTERN = re.compile(
        r"^PERIODE\s*:?\s*(?:[A-Z]+\s+)?(?P<year>20\d{2})$",
        re.IGNORECASE,
    )
    SUPPORTED_TITLE_PATTERN = re.compile(
        r"^REKENING\s+TAHAPAN(?:\s+XPRESI)?$",
        re.IGNORECASE,
    )
    DATE_ROW_PATTERN = re.compile(
        r"^(?P<day>\d{2})/(?P<month>\d{2})(?:\s+|$)(?P<body>.*)$"
    )
    MONEY_TOKEN = r"(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}"
    AMOUNT_SUFFIX_PATTERN = re.compile(
        rf"^(?P<description>.*?)\s+(?P<amount>{MONEY_TOKEN})"
        rf"(?:\s+(?P<marker>DB|CR))?"
        rf"(?:\s+(?P<balance>{MONEY_TOKEN}))?\s*$",
        re.IGNORECASE,
    )
    AMBIGUOUS_BALANCE_PATTERN = re.compile(
        rf"^(?P<description>.*?)\s+(?P<amount>{MONEY_TOKEN})"
        rf"\s+(?P<marker>DB|CR)\s+(?P<ambiguous_balance>\S.*)$",
        re.IGNORECASE,
    )
    TABLE_HEADER_PATTERN = re.compile(
        r"^TANGGAL\s+KETERANGAN\s+CBG\s+MUTASI\s+SALDO$",
        re.IGNORECASE,
    )
    EMPTY_MARKER_PATTERN = re.compile(
        r"^TRANSAKSI\s+TIDAK\s+TERSEDIA$",
        re.IGNORECASE,
    )
    NON_TRANSACTION_ROW_PATTERN = re.compile(
        r"^(?:SALDO\s+AWAL|SALDO\s+AKHIR)(?:\s|$)",
        re.IGNORECASE,
    )
    SUMMARY_PATTERN = re.compile(
        r"^(?:SALDO\s+AWAL|MUTASI\s+CR|MUTASI\s+DB|SALDO\s+AKHIR)\s*:",
        re.IGNORECASE,
    )
    FOOTER_PATTERN = re.compile(
        r"^(?:BERSAMBUNG\s+KE\s+HALAMAN\s+BERIKUT|CATATAN\s*:|HALAMAN\s*:|"
        r"MATA\s+UANG\s*:|FASILITAS\s*:|KETERANGAN\s*:|KCP\s+)",
        re.IGNORECASE,
    )
    SLASH_REFERENCE_PATTERN = re.compile(
        r"(?<![A-Z0-9])(?P<reference>[A-Z0-9]{2,12}/[A-Z0-9]{3,12}/[A-Z0-9-]{4,24})(?![A-Z0-9])",
        re.IGNORECASE,
    )
    NAMED_REFERENCE_PATTERN = re.compile(
        r"\b(?:REF(?:ERENSI)?|NO\.?\s*REF)\s*[:#-]?\s*(?P<reference>[A-Z0-9][A-Z0-9/-]{5,31})\b",
        re.IGNORECASE,
    )

    TRANSACTION_TYPE_PREFIXES = (
        "TRSF E-BANKING DB",
        "TRSF E-BANKING CR",
        "BI-FAST DB",
        "BI-FAST CR",
        "TRANSAKSI DEBIT",
        "TARIKAN ATM",
        "BIAYA ADM",
        "BUNGA",
        "KARTU KREDIT/PL",
        "PEMBAYARAN PINJ.",
        "DB OTOMATIS",
        "SETORAN TUNAI",
        "SETORAN",
    )
    INCOME_TYPES = {
        "TRSF E-BANKING CR",
        "BI-FAST CR",
        "BUNGA",
        "SETORAN TUNAI",
        "SETORAN",
    }
    EXPENSE_TYPES = {
        "TRSF E-BANKING DB",
        "BI-FAST DB",
        "TRANSAKSI DEBIT",
        "TARIKAN ATM",
        "BIAYA ADM",
        "KARTU KREDIT/PL",
        "PEMBAYARAN PINJ.",
        "DB OTOMATIS",
    }

    def parse(self, file: BinaryIO) -> ParsedImportResult:
        extraction = extract_pdf_metadata(file, line_normalizer=self._normalize_line)
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
        expected_section_id: str | None = None,
    ) -> ParsedImportResult:
        discovery = self.discover_sections(lines)
        normalized_section_id = str(expected_section_id or "").strip()

        if len(discovery.sections) > 1 and not normalized_section_id:
            raise SectionSelectionRequiredError(
                "BCA statement contains multiple account sections"
            )

        selected_section_id = (
            normalized_section_id
            or discovery.sections[0].candidate.section_id
        )
        return self.parse_selected_section(
            discovery,
            selected_section_id=selected_section_id,
            page_count=page_count,
            extracted_text_length=extracted_text_length,
        )

    def discover_sections(self, lines: list[str]) -> BcaSectionDiscovery:
        normalized_lines = [
            self._normalize_line(line)
            for line in lines
            if self._normalize_line(line)
        ]
        if not any(self.SUPPORTED_TITLE_PATTERN.match(line) for line in normalized_lines):
            raise UnsupportedStatementError("BCA statement product is not supported")

        raw_sections: list[dict[str, Any]] = []
        current_section: dict[str, Any] | None = None
        closed_identities: set[str] = set()

        for line_index, line in enumerate(normalized_lines):
            account_identity = self._extract_section_header_identity(
                normalized_lines,
                line_index=line_index,
            )

            if account_identity:
                if current_section is None:
                    current_section = {
                        "account_identity": account_identity,
                        "lines": [],
                    }
                    raw_sections.append(current_section)
                elif account_identity != current_section["account_identity"]:
                    closed_identities.add(current_section["account_identity"])
                    if account_identity in closed_identities:
                        raise UnsupportedStatementError(
                            "BCA account section reappeared after another section"
                        )
                    current_section = {
                        "account_identity": account_identity,
                        "lines": [],
                    }
                    raw_sections.append(current_section)

            if current_section is not None:
                current_section["lines"].append(line)

        if not raw_sections:
            raise UnsupportedStatementError("BCA account identity was not found")

        sections: list[BcaStatementSection] = []
        for section_index, raw_section in enumerate(raw_sections):
            section_lines = list(raw_section["lines"])
            if not any(self.TABLE_HEADER_PATTERN.match(line) for line in section_lines):
                raise UnsupportedStatementError(
                    "BCA transaction table header was not found for a section"
                )
            self._extract_statement_year(section_lines)

            account_identity = str(raw_section["account_identity"])
            transaction_count = self._estimate_transaction_count(section_lines)
            section_type = "account" if section_index == 0 else "pocket"
            display_number = 1 if section_index == 0 else section_index
            section_id = self._build_section_id(account_identity)
            candidate = ImportSectionCandidate(
                section_id=section_id,
                display_label=(
                    f"Rekening {display_number}"
                    if section_type == "account"
                    else f"Pocket {display_number}"
                ),
                masked_identity=self._mask_account_identity(account_identity),
                section_type=section_type,
                source_sequence_start=1 if transaction_count else 0,
                source_sequence_end=transaction_count,
                transaction_count_estimate=transaction_count,
                is_selectable=transaction_count > 0,
            )
            sections.append(BcaStatementSection(
                candidate=candidate,
                lines=tuple(section_lines),
                account_identity_hash=self._hash_account_identity(account_identity),
                section_identity_hash=self._hash_section_identity(account_identity),
            ))

        return BcaSectionDiscovery(sections=tuple(sections))

    def parse_selected_section(
        self,
        discovery: BcaSectionDiscovery,
        *,
        selected_section_id: str,
        page_count: int = 0,
        extracted_text_length: int = 0,
    ) -> BcaParsedImportResult:
        selected_section = next(
            (
                section
                for section in discovery.sections
                if section.candidate.section_id == selected_section_id
            ),
            None,
        )
        if selected_section is None:
            raise InvalidSectionSelectionError(
                "Selected BCA section was not found in server discovery"
            )

        section_lines = list(selected_section.lines)
        statement_year = self._extract_statement_year(section_lines)
        transactions, warnings, malformed_rows = self._parse_transaction_blocks(
            section_lines,
            statement_year=statement_year,
            account_identity_hash=selected_section.account_identity_hash,
            section_identity_hash=selected_section.section_identity_hash,
        )
        statement_empty = bool(
            not transactions
            and any(self.EMPTY_MARKER_PATTERN.match(line) for line in section_lines)
        )

        if not transactions and malformed_rows:
            raise MalformedTransactionRowError(
                "BCA statement contains transaction rows that cannot be parsed safely"
            )

        if not transactions and (
            not statement_empty or len(discovery.sections) > 1
        ):
            raise NoParseableTransactionsError(
                "Selected BCA section yielded no parseable transactions"
            )

        self._assign_occurrence_indexes(transactions)

        return BcaParsedImportResult(
            provider=self.provider,
            transactions=transactions,
            page_count=page_count,
            extracted_text_length=extracted_text_length,
            statement_empty=statement_empty,
            warnings=warnings,
            provider_metadata=dict(self.PROVIDER_METADATA),
            section_candidates=discovery.candidates,
            selected_section=selected_section.candidate,
            is_multi_account=len(discovery.sections) > 1,
        )

    def _estimate_transaction_count(self, lines: list[str]) -> int:
        return sum(
            1
            for line in lines
            if (
                (date_match := self.DATE_ROW_PATTERN.match(line))
                and not self.NON_TRANSACTION_ROW_PATTERN.match(
                    date_match.group("body").strip()
                )
            )
        )

    def _extract_section_header_identity(
        self,
        lines: list[str],
        *,
        line_index: int,
    ) -> str:
        account_match = self.ACCOUNT_PATTERN.search(lines[line_index])
        if account_match is None:
            return ""

        has_period = False
        for metadata_line in lines[line_index + 1:line_index + 25]:
            if (
                self.DATE_ROW_PATTERN.match(metadata_line)
                or self.SUMMARY_PATTERN.match(metadata_line)
                or self.EMPTY_MARKER_PATTERN.match(metadata_line)
                or self.ACCOUNT_PATTERN.search(metadata_line)
            ):
                return ""
            if self.PERIOD_PATTERN.match(metadata_line):
                has_period = True
                continue
            if self.TABLE_HEADER_PATTERN.match(metadata_line):
                if not has_period:
                    return ""
                break
        else:
            return ""

        if not has_period:
            return ""

        return re.sub(r"\D", "", account_match.group("account"))

    def _extract_statement_year(self, lines: list[str]) -> int:
        years = {
            int(period_match.group("year"))
            for line in lines
            if (period_match := self.PERIOD_PATTERN.match(line))
        }
        if len(years) != 1:
            raise UnsupportedStatementError("BCA statement period is missing or ambiguous")
        return years.pop()

    def _parse_transaction_blocks(
        self,
        lines: list[str],
        *,
        statement_year: int,
        account_identity_hash: str,
        section_identity_hash: str,
    ) -> tuple[list[dict], list[str], int]:
        transactions: list[dict] = []
        warnings: list[str] = []
        malformed_rows = 0
        current_block: list[str] = []
        account_header_indexes = {
            line_index
            for line_index in range(len(lines))
            if self._extract_section_header_identity(lines, line_index=line_index)
        }

        def flush_current_block():
            nonlocal current_block, malformed_rows
            if not current_block:
                return

            try:
                transaction = self._build_transaction(
                    current_block,
                    statement_year=statement_year,
                    account_identity_hash=account_identity_hash,
                    section_identity_hash=section_identity_hash,
                    source_sequence=len(transactions) + 1,
                )
            except MalformedTransactionRowError:
                malformed_rows += 1
                if "malformed_transaction_row" not in warnings:
                    warnings.append("malformed_transaction_row")
            else:
                if transaction is not None:
                    for warning in transaction.pop("_parse_warnings", []):
                        if warning not in warnings:
                            warnings.append(warning)
                    transactions.append(transaction)
            current_block = []

        for line_index, line in enumerate(lines):
            if self.DATE_ROW_PATTERN.match(line):
                flush_current_block()
                current_block = [line]
                continue

            if self._is_structural_line(
                line,
                is_account_header=line_index in account_header_indexes,
            ):
                flush_current_block()
                continue

            if current_block:
                current_block.append(line)

        flush_current_block()
        return transactions, warnings, malformed_rows

    def _build_transaction(
        self,
        block_lines: list[str],
        *,
        statement_year: int,
        account_identity_hash: str,
        section_identity_hash: str,
        source_sequence: int,
    ) -> dict | None:
        date_match = self.DATE_ROW_PATTERN.match(block_lines[0])
        if date_match is None:
            return None

        first_line_body = date_match.group("body").strip()
        if self.NON_TRANSACTION_ROW_PATTERN.match(first_line_body):
            return None

        amount_match = self.AMOUNT_SUFFIX_PATTERN.match(first_line_body)
        parse_warnings: list[str] = []
        if amount_match is None:
            amount_match = self.AMBIGUOUS_BALANCE_PATTERN.match(first_line_body)
            if amount_match is None:
                raise MalformedTransactionRowError(
                    "BCA transaction amount is missing or ambiguous"
                )
            parse_warnings.append("ambiguous_balance")

        transaction_date = self._normalize_transaction_date(
            day=date_match.group("day"),
            month=date_match.group("month"),
            year=statement_year,
        )
        transaction_type = self._resolve_transaction_type(
            amount_match.group("description")
        )
        if not transaction_type and amount_match.group("marker"):
            transaction_type = amount_match.group("marker").upper()
        direction = self._resolve_direction(
            transaction_type=transaction_type,
            marker=amount_match.group("marker"),
        )
        amount = self._parse_money(amount_match.group("amount"))
        balance_after = (
            self._parse_money(amount_match.group("balance"))
            if "balance" in amount_match.groupdict() and amount_match.group("balance")
            else None
        )
        description_lines = [amount_match.group("description").strip()]
        description_lines.extend(block_lines[1:])
        merchant_original = " ".join(
            part for part in description_lines if str(part or "").strip()
        ).strip()
        if not merchant_original:
            merchant_original = transaction_type
        source_reference = self._extract_source_reference(description_lines)
        merchant_original = self._mask_account_number_references(merchant_original)
        sanitized_raw_text = self._mask_account_number_references(
            " | ".join(block_lines)
        )

        return {
            "transaction_date": transaction_date,
            "transaction_time": None,
            "datetime": f"{transaction_date} 00:00",
            "merchant_original": merchant_original,
            "amount": amount,
            "direction": direction,
            "transaction_type": transaction_type,
            "review_group": self.REVIEW_GROUP,
            "raw_text": sanitized_raw_text,
            "source_reference": source_reference,
            "balance_after": balance_after,
            "source_sequence": source_sequence,
            "source_occurrence": 1,
            "_account_identity_hash": account_identity_hash,
            "_section_identity": section_identity_hash,
            "_parse_warnings": parse_warnings,
            **self.PROVIDER_METADATA,
        }

    def _assign_occurrence_indexes(self, transactions: list[dict]):
        occurrences: dict[str, int] = defaultdict(int)
        for transaction in transactions:
            signature = build_bca_signature_key(
                account_identity_hash=transaction["_account_identity_hash"],
                section_identity=transaction["_section_identity"],
                transaction_date=transaction["transaction_date"],
                merchant_name=transaction["merchant_original"],
                amount=transaction["amount"],
                direction=transaction["direction"],
                source_reference=transaction.get("source_reference"),
                balance_after=transaction.get("balance_after"),
            )
            occurrences[signature] += 1
            transaction["source_occurrence"] = occurrences[signature]

    def _resolve_transaction_type(self, description: str) -> str:
        normalized_description = self._normalize_line(description).upper()
        for transaction_type in self.TRANSACTION_TYPE_PREFIXES:
            if normalized_description.startswith(transaction_type):
                return transaction_type

        if re.search(r"(?:^|\s)DB(?:\s|$)", normalized_description):
            return "DB"
        if re.search(r"(?:^|\s)CR(?:\s|$)", normalized_description):
            return "CR"
        return ""

    def _resolve_direction(self, *, transaction_type: str, marker: str | None) -> str:
        normalized_marker = str(marker or "").strip().upper()
        if normalized_marker == "DB":
            return "expense"
        if normalized_marker == "CR":
            return "income"
        if transaction_type in self.INCOME_TYPES or transaction_type == "CR":
            return "income"
        if transaction_type in self.EXPENSE_TYPES or transaction_type == "DB":
            return "expense"
        raise MalformedTransactionRowError("BCA transaction direction is ambiguous")

    def _extract_source_reference(self, description_lines: list[str]) -> str | None:
        description = " ".join(description_lines).upper()
        for pattern in (self.SLASH_REFERENCE_PATTERN, self.NAMED_REFERENCE_PATTERN):
            reference_match = pattern.search(description)
            if not reference_match:
                continue

            normalized_reference = re.sub(
                r"\s*([/-])\s*",
                r"\1",
                self._normalize_line(reference_match.group("reference")),
            ).upper()
            if any(character.isalpha() for character in normalized_reference):
                return normalized_reference
        return None

    def _normalize_transaction_date(self, *, day: str, month: str, year: int) -> str:
        try:
            parsed_date = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
        except ValueError as exc:
            raise MalformedTransactionRowError("BCA transaction date is invalid") from exc
        return parsed_date.strftime("%d/%m/%Y")

    def _parse_money(self, raw_value: str) -> float:
        normalized_value = str(raw_value or "").replace(",", "")
        try:
            return float(Decimal(normalized_value))
        except InvalidOperation as exc:
            raise MalformedTransactionRowError("BCA amount is invalid") from exc

    def _hash_account_identity(self, account_identity: str) -> str:
        return hashlib.sha256(f"bca:{account_identity}".encode("utf-8")).hexdigest()

    def _hash_section_identity(self, account_identity: str) -> str:
        return hashlib.sha256(
            f"bca-section:{account_identity}".encode("utf-8")
        ).hexdigest()

    def _build_section_id(self, account_identity: str) -> str:
        digest = hashlib.sha256(
            f"bca-section-id-v1:{account_identity}".encode("utf-8")
        ).hexdigest()
        return f"bca-section-{digest[:24]}"

    def _mask_account_identity(self, account_identity: str) -> str:
        visible_suffix = account_identity[-4:]
        return f"**** {visible_suffix}"

    def _mask_account_number_references(self, value: str) -> str:
        def replace_account(match: re.Match) -> str:
            matched_value = match.group(0)
            account_offset = match.start("account") - match.start(0)
            account_identity = re.sub(r"\D", "", match.group("account"))
            return (
                matched_value[:account_offset]
                + self._mask_account_identity(account_identity)
            )

        return self.ACCOUNT_PATTERN.sub(replace_account, str(value or ""))

    def _is_structural_line(
        self,
        line: str,
        *,
        is_account_header: bool = False,
    ) -> bool:
        return bool(
            is_account_header
            or self.PERIOD_PATTERN.match(line)
            or self.SUPPORTED_TITLE_PATTERN.match(line)
            or self.TABLE_HEADER_PATTERN.match(line)
            or self.EMPTY_MARKER_PATTERN.match(line)
            or self.SUMMARY_PATTERN.match(line)
            or self.FOOTER_PATTERN.match(line)
            or line.upper() == "BCA"
        )

    def _normalize_line(self, value: str) -> str:
        return " ".join(str(value or "").replace("\xa0", " ").split())
