# Plugin Control Center

The control center presents PaperForge health, actions, and configuration using user-facing concepts rather than implementation vocabulary.

## Language

**Foundation**:
The persistent capability that makes PaperForge operational on this device, including its managed environment and required integration state.
_Avoid_: Installation, runtime

**Installation**:
A one-time recovery action shown only when the Foundation does not yet exist.
_Avoid_: Installation module, installation page

**Managed Runtime**:
A technical implementation detail of the Foundation, exposed only in advanced diagnostics or recovery.
_Avoid_: Runtime as a primary navigation destination

**Module Detail**:
A contextual drill-down for one operational module, entered from Overview or Maintenance rather than a permanent top-level destination.
_Avoid_: Module Detail tab, defaulting detail navigation to Foundation

**Setup Journey**:
A four-stage guided first-use experience: establish Foundation, connect Library, configure only the Optional Capabilities the user selects, then review and begin normal operation.
_Avoid_: Fixed empty steps for skipped capabilities, exposing all configuration and diagnostics during first use

**Setup Completion**:
A durable transition from the Setup Journey to normal operation; later health failures never reverse it automatically.
_Avoid_: Inferring first-use state from current module health

**Operational Baseline**:
The minimum completed setup: a ready Foundation and a connected literature library. Optional capabilities do not block Setup Completion.
_Avoid_: Requiring every capability before PaperForge can be used

**Control Center Summary**:
The overall statement of whether the Operational Baseline is usable, followed by the count of enabled-module problems in Maintenance. Not Enabled optional capabilities never lower this summary.
_Avoid_: Aggregating the worst status across all modules, “all modules ready” as the usability requirement

**Module Card**:
A navigation-only overview of one operational module, showing its Module Status, a plain-language summary, and at most one key metric. The whole card opens Module Detail and never executes an operation.
_Avoid_: Check buttons, repair actions, or competing click targets inside overview cards

**Optional Capability**:
An independently enabled feature such as OCR, Smart Retrieval, or Agent Integration whose absence is explained but never blocks the Operational Baseline or enters Maintenance.
_Avoid_: Treating skipped optional setup as installation failure or unresolved maintenance

**Operational Module**:
An independently understandable capability with its own availability, health, setup, and recovery lifecycle. The five modules are Foundation, Library, OCR, Smart Retrieval, and Agent Integration.
_Avoid_: Treating Maintenance or Help as modules

**Agent Integration**:
The optional operational module that manages a target AI agent platform, deployment state, and the available system and user Skills.
_Avoid_: Hiding Agent Integration inside Foundation diagnostics, claiming a live connection when integration is file deployment

**Maintenance**:
An actionable projection of enabled module problems that block use, fail a requested task, make an output unusable, or create material data risk. It contains no optimization suggestions and is not an independently healthy or unhealthy module.
_Avoid_: Maintenance module, feature recommendations, non-actionable quality warnings

**Maintenance Action**:
A safe, reversible retry may run in place; configuration, scoped, batch, or destructive work navigates to the owning module or Operational Workspace with the affected context preserved.
_Avoid_: Blind destructive execution from Maintenance, routing every trivial retry through another page

**Help**:
A task-oriented support destination for getting started, completing common workflows, resolving current user-visible problems, and copying a privacy-safe diagnostic report.
_Avoid_: Help module, capability status badges, raw log console as the default surface

**Refresh Status**:
A single control-center action that re-evaluates every operational module; individual retry appears only for a module whose detection failed.
_Avoid_: Check, Check Status, Re-check, per-module refresh controls in normal states

**Module Status**:
One of six user-facing states shared by every operational module: Checking, Ready, Not Enabled, Setup Required, Action Required, or Detection Failed.
_Avoid_: Pending, Unknown, stale as a visible status, or module-specific badge vocabularies

**Capability Action**:
A backend-authorized operation identified by a stable action ID and safety metadata, with localized user-facing copy supplied by the plugin.
_Avoid_: Raw CLI commands as labels, backend-only English labels, or actions inferred from status

**Module Detail Shell**:
The fixed cross-module frame containing return navigation, the five-module switcher, title, Module Status, primary action area, and advanced diagnostics entry. Each module owns a task-specific body inside this frame.
_Avoid_: Forcing identical body layouts or moving shell controls between modules

**Module-Owned Configuration**:
Configuration is edited only within the operational module that owns its meaning: Zotero in Library, OCR credentials in OCR, vector settings in Memory, and platform plus Skills in Agent Integration. Foundation owns only the PaperForge environment.
_Avoid_: A duplicate all-settings section inside Foundation

**Contextual Primary Action**:
The single operation currently recommended for a module; it is absent when the module is Ready and changes only with backend-authorized module state.
_Avoid_: Persistent maintenance buttons, action menus requiring users to diagnose the problem, or multiple competing primary actions

**Library**:
The Zotero-connected literature corpus available to PaperForge, presented through connection state, corpus size, synchronization activity, and source configuration.
_Avoid_: Library Index as the primary user-facing name, database-centric health dashboards

**OCR Module**:
The control-center surface for OCR availability, summary statistics, service configuration, and entry into paper-level OCR work.
_Avoid_: Embedding the full paper queue inside Settings

**Operational Workspace**:
A full-width PaperForge view for high-volume, paper-level work such as filtering, selecting, and reprocessing OCR records. Module Detail links to it but does not duplicate it.
_Avoid_: Long operational tables and nested scrolling inside the Settings dialog

**Smart Retrieval**:
The user-facing operational module that enables paper lookup, content discovery, paper navigation, and scoped evidence fetch across the Library.
_Avoid_: Memory Layer, Semantic Retrieval as the umbrella name, Vector Database

**Support Diagnostic**:
A one-click, privacy-safe clipboard report containing versions, module status, stable error code, recent action, exit information, and a bounded error excerpt. It excludes secrets, document content, local identity, and raw absolute paths.
_Avoid_: Asking users to interpret diagnostics, copying raw logs, or requiring a preview step before routine support handoff

**User-visible Problem**:
A plain-language message structured as what happened, what is and is not affected, and the single next step. A Support Diagnostic is adjacent but never required for understanding.
_Avoid_: Bare failure labels, raw exception text, or error codes as explanation

**Module Activity**:
Visible work in progress, presented separately from Module Status with task label, bounded progress, affected scope, and a safe stop control when supported. Activity enters Maintenance only after a terminal failure.
_Avoid_: Replacing availability with “Running”, treating in-progress work as unresolved maintenance, notification-only long tasks

**Impact Confirmation**:
A confirmation for high-impact work that names the affected scope, replaced derived outputs, preserved source and user data, interruptibility, and a concrete action verb.
_Avoid_: Generic “Are you sure?”, technical destructive labels without preservation facts, typed confirmation for regenerable artifacts

**Configuration Summary**:
A safe, read-only presentation of module-owned settings with an explicit Change entry. Editing is local to one configuration group and ends with Cancel or Save and Verify; credentials show configured state, never plaintext.
_Avoid_: Always-editable settings walls, saving unvalidated drafts on every keystroke, repopulating stored secrets

**Navigation Memory**:
The persisted last top-level destination or selected operational module. Reopening refreshes current state and never restores drafts, selections, confirmations, diagnostics disclosure, scroll position, or other transient interaction state.
_Avoid_: Always reopening at Overview, restoring stale or sensitive interaction state

**Interface Language**:
The plugin presentation language, inherited from Obsidian by default with an explicit PaperForge override. Backend reason and action IDs are localized by the plugin rather than displayed as backend prose.
_Avoid_: Mixed-language surfaces, raw backend labels, forcing a language choice during first use

**Last Known Status**:
The most recent successful module result shown immediately while a background refresh runs. Refresh activity is separate; on Detection Failed, the last successful status remains explicitly timestamped as historical reference.
_Avoid_: Converting stale cache into Not Enabled or Detection Failed before a refresh attempt, blanking every card on open
