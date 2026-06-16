from __future__ import annotations


BLU_CONTENT_MARKERS = (
    "bluaccount | bluspending",
    "bluspending -",
    "bca digital",
    "blubybcadigital.id",
    "haloblu",
)


def detect_import_provider(*, filename: str, extracted_text: str = "") -> dict:
    normalized_filename = str(filename or "").lower()

    if normalized_filename.endswith(".pdf") and "blu" in normalized_filename:
        return {
            "provider": "blu",
            "detection_source": "filename",
        }

    normalized_text = str(extracted_text or "").lower()

    if any(marker in normalized_text for marker in BLU_CONTENT_MARKERS):
        return {
            "provider": "blu",
            "detection_source": "content",
        }

    return {
        "provider": "unknown",
        "detection_source": "unknown",
    }
