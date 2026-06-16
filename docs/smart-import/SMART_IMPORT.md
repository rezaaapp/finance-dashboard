# Smart Import Foundation

## Feature Overview

Smart Import is a generic transaction import foundation for files from financial providers. Sprint 1 creates the import job lifecycle, parser contract, upload endpoint, and landing page without implementing provider-specific parsing.

The first visible provider is Blu PDF Statement in beta. The upload control currently opens a file picker only on the frontend, while the backend exposes a generic upload API for future integration.

## Future Providers

Planned sources include:

- Blu PDF Statement
- BCA PDF
- SeaBank PDF
- GoPay PDF
- OVO PDF
- OCR-based statement import
- CSV import

## Generic Architecture

Backend modules live under `backend/app/imports/`:

- `parsers/base_parser.py`: abstract parser contract for future provider parsers.
- `services/import_service.py`: receives uploaded files, detects provider, calls a parser hook, and creates import jobs.
- `repositories/import_repository.py`: persistence boundary for import jobs.
- `models/import_models.py`: generic import job, status enum, and parsed result models.
- `utils/fingerprint.py`: placeholder for future fingerprinting work.

The import job model tracks:

- `id`
- `workspace_id`
- `provider`
- `filename`
- `status`
- `created_at`
- `completed_at`

Supported job statuses are:

- `uploaded`
- `parsing`
- `review`
- `approved`
- `completed`
- `failed`
- `expired`

## Why Parser-Based Architecture

A parser-based architecture keeps provider-specific logic isolated from import orchestration. Each provider can implement the same `BaseParser.parse(file)` contract and return a normalized parsed result:

```json
{
  "provider": "",
  "transactions": []
}
```

This lets the service layer handle shared concerns such as job creation, provider selection, review flow integration, and future approval or sync steps without coupling those workflows to Blu, BCA, SeaBank, GoPay, OCR, or CSV details.

## Roadmap

Sprint 1:

- Create generic import module.
- Add import job persistence.
- Add upload API.
- Add Smart Import landing page.
- Keep parser output empty.

Future sprints:

- Add Blu PDF parser.
- Add review and approval workflow.
- Add parsed transaction persistence.
- Add duplicate detection and fingerprinting.
- Add Spreadsheet Sync integration.
- Add additional provider parsers.
- Add OCR support.
