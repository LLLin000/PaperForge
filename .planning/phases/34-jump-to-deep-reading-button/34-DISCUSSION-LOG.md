# Phase 34: Jump to Deep Reading Button - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-05-06
**Phase:** 34-jump-to-deep-reading-button
**Areas discussed:** Button placement, Label & i18n strategy

## Button Placement & Relationship to Existing Button

| Option | Description | Selected |
|--------|-------------|----------|
| Replace: jump button in the next-step card | Replace "Copy Key for /pf-deep" when deep_reading_status is 'done' | ✓ |
| Dual: both in actions row AND next-step card | Redundant but discoverable | |
| Keep both: jump button in actions row, copy-key stays | Coexist with different purposes | |

**Clarification:** Jump button replaces **Copy Context** in `ready` state (not `/pf-deep` state). Copy-key in `/pf-deep` state unchanged.

## Label & i18n Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded Chinese | Follow deep-reading mode pattern | |
| Add to i18n: 跳转到精读 / Open Deep Reading | Add to t() language pack | ✓ |
| Hardcoded English | Follow actions row pattern | |

## Icon Choice

| Option | Description | Selected |
|--------|-------------|----------|
| Magnifying glass | Search/lookup icon | ✓ |
| Book | Reading icon | |
| Eye | View/review icon | |
