# Context Map

## Contexts

- [OCR Quality Report](./CONTEXT.md) — quality signals, quality indicators, readiness policy, and human validation for OCR outputs.
- [Materialization](./paperforge/CONTEXT.md) — per-paper truth about the OCR → retrieval → vector → serving pipeline: what exists at each layer, whether it is trustworthy, and the minimal repair (raw → derived → published → retrieval → vector → serving).
- [Retrieval Layer](./paperforge/memory/CONTEXT.md) — paper-native retrieval units, lookup intents, corpus recall, and structured paper navigation.
- [Plugin Control Center](./paperforge/plugin/CONTEXT.md) — presents device foundation, module health, recovery actions, and configuration in user-facing language
- [Standalone Onboarding & Client-Neutral Setup Protocol](./paperforge/setup/CONTEXT.md) — installation and first configuration as a backend-owned, client-neutral lifecycle: Foundation vs client integration, onboarding protocol, secret contract, relocation, S1–S8 certification.

## Relationships

- **OCR Quality Report → Retrieval Layer**: OCR quality produces diagnostics and boundary facts that the retrieval layer may use for local junk veto and build health, but not for paper-level trust penalties.
- **Materialization → OCR Quality Report**: Materialization consumes OCR lifecycle/provenance facts to judge the raw/derived layers; it does not redefine OCR quality.
- **Materialization → Retrieval Layer**: Retrieval materialization (manifest + units) is judged by Materialization's retrieval layer; retrieval does not redefine OCR readiness as retrieval importance.
- **Materialization → Plugin Control Center**: The first-broken-frontier state and minimal repair action are presented as module health and contextual actions.
- **Retrieval Layer ↔ OCR Quality Report**: Retrieval consumes structured OCR outputs and structure boundaries; it must not redefine OCR readiness as retrieval importance.
- **OCR Quality Report → Plugin Control Center**: OCR readiness and recovery facts are presented as module health and contextual actions without redefining their meaning.
- **Retrieval Layer → Plugin Control Center**: Retrieval readiness and maintenance facts are presented as Memory health and contextual actions without exposing storage implementation as primary navigation.
- **Standalone Onboarding → Materialization**: onboarding produces the canonical config that materialization consumes; Foundation verify must observe the same canonical states.
- **Standalone Onboarding → Plugin Control Center**: the control center becomes one client of the onboarding protocol, not its owner.
- **Standalone Onboarding ↔ OCR Quality Report / Retrieval Layer**: capability readiness (OCR READY / Vector READY) is reported by the onboarding lifecycle without redefining their meaning.
