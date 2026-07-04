# Context Map

## Contexts

- [OCR Quality Report](./CONTEXT.md) — quality signals, quality indicators, readiness policy, and human validation for OCR outputs.
- [Retrieval Layer](./paperforge/memory/CONTEXT.md) — paper-native retrieval units, lookup intents, corpus recall, and structured paper navigation.

## Relationships

- **OCR Quality Report → Retrieval Layer**: OCR quality produces diagnostics and boundary facts that the retrieval layer may use for local junk veto and build health, but not for paper-level trust penalties.
- **Retrieval Layer ↔ OCR Quality Report**: Retrieval consumes structured OCR outputs and structure boundaries; it must not redefine OCR readiness as retrieval importance.
