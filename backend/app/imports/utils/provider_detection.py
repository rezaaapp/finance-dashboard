from __future__ import annotations

from app.imports.provider_registry import list_import_provider_configs


def detect_import_provider(*, filename: str, extracted_text: str = "") -> dict:
    normalized_filename = str(filename or "").lower()
    normalized_filename_words = normalized_filename.replace("-", " ").replace("_", " ")
    provider_configs = [
        provider_config
        for provider_config in list_import_provider_configs()
        if provider_config.import_enabled and provider_config.parser_available
    ]
    filename_matches = []

    if normalized_filename.endswith(".pdf"):
        for provider_config in provider_configs:
            if provider_config.key == "bca" and "bca digital" in normalized_filename_words:
                continue
            if any(marker in normalized_filename for marker in provider_config.filename_markers):
                filename_matches.append(provider_config.key)

    normalized_text = str(extracted_text or "").lower()
    content_matches = []

    for provider_config in provider_configs:
        if any(marker in normalized_text for marker in provider_config.content_markers):
            content_matches.append(provider_config.key)

    filename_provider = filename_matches[0] if len(filename_matches) == 1 else None
    content_provider = content_matches[0] if len(content_matches) == 1 else None
    is_ambiguous = len(filename_matches) > 1 or len(content_matches) > 1
    is_mismatch = bool(
        filename_provider
        and content_provider
        and filename_provider != content_provider
    )

    if is_ambiguous or is_mismatch:
        return {
            "provider": "unknown",
            "detection_source": "mismatch",
            "error_code": "provider_mismatch",
            "filename_provider": filename_provider or "unknown",
            "content_provider": content_provider or "unknown",
        }

    if filename_provider:
        return {
            "provider": filename_provider,
            "detection_source": "filename",
        }

    if content_provider:
        return {
            "provider": content_provider,
            "detection_source": "content",
        }

    return {
        "provider": "unknown",
        "detection_source": "unknown",
    }
