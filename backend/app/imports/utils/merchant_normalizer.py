from __future__ import annotations

import re


class MerchantNormalizer:
    TRAILING_PATTERNS = [
        re.compile(r"\s+(?:[A-Z]{2,6}\s+)?QR(?:IS)?$", re.IGNORECASE),
        re.compile(r"\s+(?:NO\.?|REF(?:ERENCE)?|ID|INV|TRX)\s*[:#-]?\s*[A-Z0-9-]+$", re.IGNORECASE),
        re.compile(r"\s+[A-Z]{2,6}\s+REF$", re.IGNORECASE),
        re.compile(r"\s+\d{3,}$"),
    ]

    def normalize(self, merchant_name: str) -> dict[str, str]:
        merchant_original = self._clean_spaces(merchant_name)
        merchant_normalized = merchant_original

        if not merchant_original:
            return {
                "merchant_original": "",
                "merchant_normalized": "",
            }

        previous_value = None
        while merchant_normalized and merchant_normalized != previous_value:
            previous_value = merchant_normalized

            for pattern in self.TRAILING_PATTERNS:
                merchant_normalized = pattern.sub("", merchant_normalized).strip()

        merchant_normalized = self._clean_spaces(merchant_normalized) or merchant_original

        return {
            "merchant_original": merchant_original,
            "merchant_normalized": merchant_normalized,
        }

    def _clean_spaces(self, value: str) -> str:
        return " ".join(str(value or "").strip().split())
