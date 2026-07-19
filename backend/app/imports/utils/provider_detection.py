from __future__ import annotations

from app.imports.provider_registry import list_import_provider_configs


def detect_import_provider(*, filename: str, extracted_text: str = "") -> dict:
    normalized_filename = str(filename or "").lower()

    if normalized_filename.endswith(".pdf"):
        for provider_config in list_import_provider_configs():
            if not provider_config.import_enabled or not provider_config.parser_available:
                continue

            if any(marker in normalized_filename for marker in provider_config.filename_markers):
                return {
                    "provider": provider_config.key,
                    "detection_source": "filename",
                }

    normalized_text = str(extracted_text or "").lower()

    for provider_config in list_import_provider_configs():
        if not provider_config.import_enabled or not provider_config.parser_available:
            continue

        if any(marker in normalized_text for marker in provider_config.content_markers):
            return {
                "provider": provider_config.key,
                "detection_source": "content",
            }

    return {
        "provider": "unknown",
        "detection_source": "unknown",
    }
