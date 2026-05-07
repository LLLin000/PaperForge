# Phase 35: AI Discussion Recorder - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-05-06
**Phase:** 35-ai-discussion-recorder
**Areas discussed:** API surface, Agent integration, File sync, Q&A data model

## API Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Function + CLI via argparse | Dual-mode: importable + CLI subcommand | ✓ |
| Pure function only | Just record_session() | |
| Class-based API | DiscussionRecorder class | |

## Agent Integration

- Only pf-paper records (pf-deep excluded per user)
- Update pf-paper.md prompt with recording step
- Agent accumulates Q&A, calls CLI at session end

## File Sync Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Independent writes | JSON and MD from same data, written separately | ✓ |
| JSON as source of truth | MD derived from JSON | |

## Q&A Data Model

- Session metadata includes: paper_key, paper_title, domain
- qa_pair source values: user_question / agent_analysis
- Timestamps: ISO 8601

## Deferred Ideas

- Direct agent-paper discussion recording (non pf-* scenario)
