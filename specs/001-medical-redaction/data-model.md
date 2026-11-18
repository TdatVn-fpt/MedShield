# Data model

Canonical field constraints are defined once in [API contract](../../docs/api-contract.md). This file provides stable citations, not duplicate constraints.

- `AnalyzeRequest.text`, `.language`, `.mode`: API contract analyze request.
- `Entity.start`, `.end`, `.label`, `.source`, `.score`: API contract Entity.
- `RedactRequest.entities`: API contract redact request and overlap validation.
- `RedactResponse.redacted_text`, `.metadata`: API contract output.
- `Engine.name`, `.status`, `.mode`, `.language`: API contract engine metadata.

State: input edit → no entities/preview/approval; analyze → current entities/preview; entity edit → unapproved preview pending; redact success → current preview; explicit approval → export. Any input/entity edit or stale-response mismatch prevents export of previous state.
