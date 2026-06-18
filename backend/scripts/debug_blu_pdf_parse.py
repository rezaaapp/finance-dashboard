from __future__ import annotations

from pathlib import Path
import json
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.imports.parsers.blu_pdf_parser import BluPdfParser
from app.imports.utils.provider_detection import detect_import_provider


def main():
    if len(sys.argv) != 2:
        print("Usage: python backend/scripts/debug_blu_pdf_parse.py \"path/to/blu.pdf\"")
        return 2

    pdf_path = Path(sys.argv[1])

    if not pdf_path.is_file():
        print(f"File not found: {pdf_path}")
        return 1

    parser = BluPdfParser()

    with pdf_path.open("rb") as file:
        extraction = parser.extract_pdf_metadata(file)

    provider_detection = detect_import_provider(
        filename=pdf_path.name,
        extracted_text=extraction["extracted_text"],
    )
    parsed_result = parser.parse_extracted_lines(
        extraction["lines"],
        page_count=extraction["page_count"],
        extracted_text_length=extraction["extracted_text_length"],
    )
    preview = [
        {
            "datetime": transaction["datetime"],
            "merchant_original": transaction["merchant_original"],
            "amount": transaction["amount"],
            "direction": transaction["direction"],
            "transaction_type": transaction["transaction_type"],
            "review_group": transaction["review_group"],
        }
        for transaction in parsed_result.transactions[:5]
    ]
    output = {
        "provider": provider_detection["provider"],
        "detection_source": provider_detection["detection_source"],
        "page_count": extraction["page_count"],
        "extracted_text_length": extraction["extracted_text_length"],
        "transactions_found": len(parsed_result.transactions),
        "review_groups_found": sorted({
            transaction["review_group"]
            for transaction in parsed_result.transactions
            if transaction.get("review_group")
        }),
        "preview": preview,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
