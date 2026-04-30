# Feature Research — v1.5 Obsidian Plugin Settings Tab

**Domain:** Obsidian plugin UX — settings tab with setup wizard integration
**Researched:** 2026-04-29
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Must Have)

| Feature | Why | Complexity |
|---------|-----|------------|
| Settings tab opens from plugin settings | Standard Obsidian UX — every plugin with config has this | LOW — `PluginSettingTab` is 1 class |
| All wizard fields rendered as form inputs | Users expect to see every config option they'd enter in CLI wizard | LOW — `Setting.addText()` per field |
| Field labels are clear and beginner-friendly | Target user is a novice researcher | LOW — Chinese labels with English tooltips |
| Settings persist across Obsidian restarts | Users shouldn't re-enter config every session | LOW — `loadData/saveData` |
| Default values pre-filled | Reduces friction; matches setup_wizard.py defaults | LOW — `DEFAULT_SETTINGS` object |
| "Install" button triggers setup | Core value prop — one click replaces terminal wizard | MEDIUM — subprocess orchestration |
| Install progress feedback | Users need to know the setup isn't frozen | MEDIUM — step-by-step notices |

### Differentiators (Valuable Polish)

| Feature | Value | Complexity |
|---------|-------|------------|
| Human-readable notices, never raw terminal output | User explicitly requested this; major UX differentiator vs CLI | MEDIUM — error pattern matching + friendly messages |
| Step-by-step progress ("Creating directories... ✓", "Writing config... ✓") | Makes complex setup feel manageable | LOW — notice per setup step |
| Field validation before install (path exists, API key format) | Prevents cryptic failures mid-install | MEDIUM — validation logic |
| Chinese-language UI | Target audience is Chinese medical researchers | LOW — all labels/notices in Chinese |
| Settings tab doesn't break existing sidebar | Sidebar must work exactly as before | MEDIUM — careful scoping of SettingTab class |

### Anti-Features (Explicitly Avoid)

| Feature | Why Avoid |
|---------|-----------|
| Settings tab shows pipeline status/metrics | Sidebar already does this; duplicating creates confusion |
| Settings tab has "Run Sync" / "Run OCR" buttons | Sidebar action cards already do this |
| Real-time settings sync between tabs | Unnecessary complexity for a single-user tool |
| Multi-language i18n system | Chinese-only is sufficient for target audience; i18n can be added later |

## Feature Dependencies

```
PluginSettingTab class (settings UI shell)
    └──requires──> DEFAULT_SETTINGS model (data shape)
    └──requires──> loadData/saveData (persistence)

Form validation
    └──enhances──> Install button (prevents wasted subprocess calls)

Install button (setup orchestration)
    └──requires──> Settings persistence (reads current values)
    └──requires──> Subprocess runner (calls paperforge setup)
    └──requires──> Notice formatter (polished output)

Sidebar preservation
    └──independent──> (settings tab is additive, sidebar code unchanged)
```

---

*Feature research for: PaperForge v1.5 Obsidian Plugin Setup Integration*
*Researched: 2026-04-29*
