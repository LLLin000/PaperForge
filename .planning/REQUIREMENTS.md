# Requirements: PaperForge Lite

> **Defined:** 2026-04-29
> **Core Value:** A new user downloads one Obsidian plugin and completes full PaperForge installation without touching a terminal.

---

## Previous Milestones (Validated)

All v1.0–v1.4 requirements shipped and validated. See `MILESTONES.md` for completion details.

---

## v1.5 Requirements

### Settings Tab (SETUP)

**Goal:** Obsidian plugin settings tab exposes all setup_wizard.py configuration fields with persistence.

- [x] **SETUP-01**: Settings tab renders all setup_wizard.py fields — vault path, system_dir, resources_dir, literature_dir, control_dir, agent_config_dir, PaddleOCR API token, Zotero data directory. Each field has a clear Chinese label and tooltip.
- [x] **SETUP-02**: Settings persist across Obsidian restarts via `loadData()`/`saveData()` with `DEFAULT_SETTINGS` merge pattern. Fresh installs (null data) get pre-filled defaults without crashing.
- [ ] **SETUP-03**: Field changes update in-memory immediately; disk writes are debounced at 500ms to prevent `data.json` corruption from every-keystroke saves. Settings tab state survives tab switching without data loss.

### Install & UX (INST)

**Goal:** One-click install button with polished, human-readable feedback.

- [x] **INST-01**: "Install" button triggers full setup pipeline — writes `paperforge.json`, creates directory structure, runs environment check, generates agent configs. Button disables during execution to prevent double-clicks.
- [x] **INST-02**: All feedback is polished Chinese text via Obsidian notices — friendly step-by-step progress ("正在创建目录... ✓", "正在写入配置文件... ✓"), clear success/failure messages. Raw Python tracebacks or terminal stderr are never shown directly to the user.
- [x] **INST-03**: Install button validates all fields before spawning subprocess — reports specific field-level errors in friendly language (e.g., "未找到 Vault 路径，请检查设置"). Prevents cryptic failures mid-install.
- [x] **INST-04**: Existing sidebar (`PaperForgeStatusView`) and command palette actions (`Sync Library`, `Run OCR`) continue working unchanged alongside the new settings tab. Settings tab code is strictly self-contained — no reach into sidebar internals.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Plugin sidebar redesign | Sidebar stays as-is for v1.5; enhancement deferred to future |
| Plugin auto-update detection | Deferred to when listed on Obsidian Community Plugins |
| TypeScript migration | Plugin is pure JS CommonJS; conversion is out of scope |
| Build system (esbuild/webpack) | Plugin ships as single `main.js`; adding build step breaks current release |
| Multi-language i18n | Chinese-only is sufficient for target audience |
| Plugin published to Community Plugins | Deferred until v1.5 stabilizes settings UX |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 20 | Complete |
| SETUP-02 | Phase 20 | Complete |
| SETUP-03 | Phase 20 | Pending |
| INST-01 | Phase 21 | Complete |
| INST-02 | Phase 21 | Complete |
| INST-03 | Phase 21 | Complete |
| INST-04 | Phase 21 | Complete |

**Coverage:**
- v1.5 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---

*Requirements defined: 2026-04-29*
*Last updated: 2026-04-29 after v1.5 requirements definition*
