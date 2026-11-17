"""Capability-probe readers (P1 modularization).

Six domain modules plus the shared envelope. Behavior is unchanged from
the former paperforge/commands/probe.py; that module remains as the
compatibility facade and CLI dispatch.
"""

from __future__ import annotations

from paperforge.probes.envelope import (
    CAPABILITY_OPTIONAL,
    CAPABILITY_REQUIRED,
    LEGACY_PATH_KEYS,
    MAINTENANCE_CONSTITUENT_MODULES,
    MIN_PYTHON,
    SAFETY_DESTRUCTIVE,
    SAFETY_IRREVERSIBLE,
    SAFETY_SAFE,
    SCHEMA_VERSION,
    SUPPORTED_MODULES,
    TTL_HELP,
    TTL_INSTALLATION,
    TTL_LIBRARY,
    TTL_MAINTENANCE,
    TTL_MEMORY,
    TTL_OCR,
    USER_STATE_ACTION_REQUIRED,
    USER_STATE_CHECKING,
    USER_STATE_DETECTION_FAILED,
    USER_STATE_NOT_ENABLED,
    USER_STATE_READY,
    USER_STATE_SETUP_REQUIRED,
    VALID_SAFETY_CLASSES,
    VALID_USER_STATES,
    build_action_primary,
    build_envelope,
)
from paperforge.probes.help import probe_help
from paperforge.probes.installation import normalize_release_version, probe_installation
from paperforge.probes.library import probe_library
from paperforge.probes.maintenance import derive_maintenance, probe_maintenance
from paperforge.probes.memory import probe_memory
from paperforge.probes.ocr import (
    ocr_pipeline_version_summary,
    paper_pipeline_versions,
    probe_ocr,
)

__all__ = [
    "CAPABILITY_OPTIONAL",
    "CAPABILITY_REQUIRED",
    "LEGACY_PATH_KEYS",
    "MAINTENANCE_CONSTITUENT_MODULES",
    "MIN_PYTHON",
    "SAFETY_DESTRUCTIVE",
    "SAFETY_IRREVERSIBLE",
    "SAFETY_SAFE",
    "SCHEMA_VERSION",
    "SUPPORTED_MODULES",
    "TTL_HELP",
    "TTL_INSTALLATION",
    "TTL_LIBRARY",
    "TTL_MAINTENANCE",
    "TTL_MEMORY",
    "TTL_OCR",
    "USER_STATE_ACTION_REQUIRED",
    "USER_STATE_CHECKING",
    "USER_STATE_DETECTION_FAILED",
    "USER_STATE_NOT_ENABLED",
    "USER_STATE_READY",
    "USER_STATE_SETUP_REQUIRED",
    "VALID_SAFETY_CLASSES",
    "VALID_USER_STATES",
    "build_action_primary",
    "build_envelope",
    "derive_maintenance",
    "normalize_release_version",
    "ocr_pipeline_version_summary",
    "paper_pipeline_versions",
    "probe_help",
    "probe_installation",
    "probe_library",
    "probe_maintenance",
    "probe_memory",
    "probe_ocr",
]
