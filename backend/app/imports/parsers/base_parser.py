from abc import ABC, abstractmethod
from typing import BinaryIO

from app.imports.models.import_models import ParsedImportResult


class ImportParserError(ValueError):
    error_code = "no_parseable_transactions"
    user_message = "PDF terbaca, tapi transaksi tidak berhasil diparse."


class UnsupportedStatementError(ImportParserError):
    error_code = "unsupported_statement"
    user_message = "Format statement belum didukung untuk import."


class NoParseableTransactionsError(ImportParserError):
    error_code = "no_parseable_transactions"
    user_message = "PDF terbaca, tapi struktur transaksi tidak dapat diparse."


class MalformedTransactionRowError(ImportParserError):
    error_code = "malformed_transaction_row"
    user_message = "Ada baris transaksi yang tidak dapat dibaca dengan aman."


class SectionSelectionRequiredError(ImportParserError):
    error_code = "section_selection_required"
    user_message = "Pilih satu rekening atau Pocket BCA sebelum melanjutkan import."


class InvalidSectionSelectionError(ImportParserError):
    error_code = "invalid_section_selection"
    user_message = "Pilihan rekening atau Pocket tidak valid untuk PDF ini."


class BaseParser(ABC):
    provider = ""

    @abstractmethod
    def parse(self, file: BinaryIO) -> ParsedImportResult:
        """Parse an import file into a generic transaction payload."""
        return ParsedImportResult(provider=self.provider, transactions=[])
