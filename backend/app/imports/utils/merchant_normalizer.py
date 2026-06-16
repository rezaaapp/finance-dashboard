from __future__ import annotations

import re


class MerchantNormalizer:
    TRAILING_PATTERNS = [
        re.compile(r"\s+(?:[A-Z]{2,6}\s+)?QR(?:IS)?$", re.IGNORECASE),
        re.compile(r"\s+(?:NO\.?|REF(?:ERENCE)?|ID|INV|TRX)\s*[:#-]?\s*[A-Z0-9-]+$", re.IGNORECASE),
        re.compile(r"\s+[A-Z]{2,6}\s+REF$", re.IGNORECASE),
        re.compile(r"\s+\d{3,}$"),
    ]
    DISPLAY_TRAILING_PATTERNS = [
        re.compile(r"\s+KE\s+M\d{4,}$", re.IGNORECASE),
        re.compile(r"\s+BCY\s+QR$", re.IGNORECASE),
        re.compile(r"\s+(?:[A-Z]{2,6}\s+)?QR(?:IS)?$", re.IGNORECASE),
        re.compile(r"\s+M\d{4,}$", re.IGNORECASE),
        re.compile(r"\s+\d{4,}$"),
        re.compile(r"\s+[A-Z0-9]{12,}$", re.IGNORECASE),
    ]

    def normalize(self, merchant_name: str) -> dict[str, str]:
        merchant_original = self._clean_spaces(merchant_name)
        merchant_normalized = merchant_original
        merchant_display = merchant_original

        if not merchant_original:
            return {
                "merchant_original": "",
                "merchant_normalized": "",
                "merchant_display": "",
            }

        previous_value = None
        while merchant_normalized and merchant_normalized != previous_value:
            previous_value = merchant_normalized

            for pattern in self.TRAILING_PATTERNS:
                merchant_normalized = pattern.sub("", merchant_normalized).strip()

        merchant_normalized = self._clean_spaces(merchant_normalized) or merchant_original
        merchant_display = self._build_display_name(merchant_original) or merchant_normalized

        return {
            "merchant_original": merchant_original,
            "merchant_normalized": merchant_normalized,
            "merchant_display": merchant_display,
        }

    def _clean_spaces(self, value: str) -> str:
        return " ".join(str(value or "").strip().split())

    def _build_display_name(self, merchant_name: str) -> str:
        merchant_display = self._clean_spaces(str(merchant_name or "").split("|", 1)[0])
        merchant_display = merchant_display.replace(",", " ")
        merchant_display = self._clean_spaces(merchant_display)

        previous_value = None
        while merchant_display and merchant_display != previous_value:
            previous_value = merchant_display

            for pattern in self.DISPLAY_TRAILING_PATTERNS:
                merchant_display = pattern.sub("", merchant_display).strip()

        merchant_display = self._clean_spaces(merchant_display)

        if merchant_display.upper().startswith("WARUNG "):
            return merchant_display.title()

        return merchant_display
