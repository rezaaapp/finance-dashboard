from abc import ABC, abstractmethod
from typing import BinaryIO

from app.imports.models.import_models import ParsedImportResult


class BaseParser(ABC):
    provider = ""

    @abstractmethod
    def parse(self, file: BinaryIO) -> ParsedImportResult:
        """Parse an import file into a generic transaction payload."""
        return ParsedImportResult(provider=self.provider, transactions=[])
