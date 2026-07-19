from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from app.imports.parsers.base_parser import BaseParser
from app.imports.parsers.blu_pdf_parser import BluPdfParser


class UnknownImportProviderError(ValueError):
    error_code = "unsupported_provider"

    def __init__(self, provider: str):
        normalized_provider = str(provider or "").strip().lower() or "unknown"
        self.provider = normalized_provider
        super().__init__(f"Import provider is not registered: {normalized_provider}")


class ImportProviderUnavailableError(ValueError):
    error_code = "unsupported_provider"

    def __init__(self, provider: str):
        normalized_provider = str(provider or "").strip().lower() or "unknown"
        self.provider = normalized_provider
        super().__init__(f"Import provider is not enabled or has no parser: {normalized_provider}")


@dataclass(frozen=True, slots=True)
class ImportProviderConfig:
    key: str
    label: str
    source_fund: str
    source_origin: str
    parser_class: type[BaseParser] | None
    filename_markers: tuple[str, ...] = ()
    content_markers: tuple[str, ...] = ()
    import_enabled: bool = False

    @property
    def parser_available(self) -> bool:
        return self.parser_class is not None


_PROVIDER_REGISTRY = MappingProxyType({
    "blu": ImportProviderConfig(
        key="blu",
        label="Blu",
        source_fund="Blu",
        source_origin="blu_pdf",
        parser_class=BluPdfParser,
        filename_markers=("blu",),
        content_markers=(
            "bluaccount | bluspending",
            "bluspending -",
            "bca digital",
            "blubybcadigital.id",
            "haloblu",
        ),
        import_enabled=True,
    ),
    "bca": ImportProviderConfig(
        key="bca",
        label="BCA",
        source_fund="BCA",
        source_origin="bca_pdf",
        parser_class=None,
        import_enabled=False,
    ),
})


def list_import_provider_configs() -> tuple[ImportProviderConfig, ...]:
    return tuple(_PROVIDER_REGISTRY.values())


def get_import_provider_config(provider: str) -> ImportProviderConfig | None:
    normalized_provider = str(provider or "").strip().lower()
    return _PROVIDER_REGISTRY.get(normalized_provider)


def require_import_provider_config(provider: str) -> ImportProviderConfig:
    provider_config = get_import_provider_config(provider)

    if provider_config is None:
        raise UnknownImportProviderError(provider)

    return provider_config


def require_import_parser_class(provider: str) -> type[BaseParser]:
    provider_config = require_import_provider_config(provider)

    if not provider_config.import_enabled or provider_config.parser_class is None:
        raise ImportProviderUnavailableError(provider_config.key)

    return provider_config.parser_class
