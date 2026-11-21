//! Native Schema-v2 `paperforge.json` configuration & path authority.
//!
//! Matches `paperforge/config.py` and `paperforge/commands/config.py` wire
//! contracts byte-for-byte so `config list|get|set|unset|validate|paths|init`
//! and `paths --json` execute in `< 0.5ms` with zero Python runtime dependency.

use crate::platform::atomic_write_bytes;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

pub const PF_VERSION: &str = env!("CARGO_PKG_VERSION");
pub const SCHEMA_VERSION: i64 = 2;
pub const CONFIG_FILE: &str = "paperforge.json";

#[derive(Clone)]
pub struct FieldSpec {
    pub key: &'static str,
    pub nested_vault_config: bool,
    pub value_type: &'static str, // "path" | "string" | "boolean" | "enum"
    pub default_str: &'static str,
    pub default_bool: Option<bool>,
    pub env_var: Option<&'static str>,
    pub choices: &'static [&'static str],
    pub writable: bool,
    pub allow_empty: bool,
    pub vault_relative: bool,
}

pub const AGENT_PLATFORMS: &[&str] = &[
    "opencode",
    "claude",
    "codex",
    "cursor",
    "gemini",
    "kilo",
    "pi",
    "omp",
    "crush",
    "kimi",
    "github_copilot",
    "cline",
    "windsurf",
    "augment",
    "trae",
];

pub const PROVIDER_TYPES: &[&str] = &["openai_sdk", "requests"];
pub const ZOTERO_SOURCE_MODES: &[&str] = &["sqlite", "bbt"];
pub const DOMAIN_MODES: &[&str] = &["per_collection", "unified"];
pub const JOURNAL_METRICS_MODES: &[&str] = &["auto", "easyscholar", "local_only"];

pub const FIELD_SPECS: &[FieldSpec] = &[
    FieldSpec {
        key: "system_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: "System",
        default_bool: None,
        env_var: Some("PAPERFORGE_SYSTEM_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "resources_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: "Resources",
        default_bool: None,
        env_var: Some("PAPERFORGE_RESOURCES_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "literature_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: "Literature",
        default_bool: None,
        env_var: Some("PAPERFORGE_LITERATURE_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "control_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: "LiteratureControl",
        default_bool: None,
        env_var: Some("PAPERFORGE_CONTROL_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "base_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: "Bases",
        default_bool: None,
        env_var: Some("PAPERFORGE_BASE_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "skill_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: ".agents/skills",
        default_bool: None,
        env_var: Some("PAPERFORGE_SKILL_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "command_dir",
        nested_vault_config: true,
        value_type: "path",
        default_str: ".opencode/command",
        default_bool: None,
        env_var: Some("PAPERFORGE_COMMAND_DIR"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: true,
    },
    FieldSpec {
        key: "zotero_data_dir",
        nested_vault_config: false,
        value_type: "path",
        default_str: "",
        default_bool: None,
        env_var: Some("ZOTERO_DATA_DIR"),
        choices: &[],
        writable: true,
        allow_empty: true,
        vault_relative: false,
    },
    FieldSpec {
        key: "agent_platform",
        nested_vault_config: false,
        value_type: "enum",
        default_str: "opencode",
        default_bool: None,
        env_var: Some("PAPERFORGE_AGENT_PLATFORM"),
        choices: AGENT_PLATFORMS,
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "auto_analyze_after_ocr",
        nested_vault_config: false,
        value_type: "boolean",
        default_str: "",
        default_bool: Some(false),
        env_var: None,
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "ocr_profile",
        nested_vault_config: false,
        value_type: "string",
        default_str: "default",
        default_bool: None,
        env_var: Some("PAPERFORGE_OCR_PROFILE"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "paddleocr_job_url",
        nested_vault_config: false,
        value_type: "string",
        default_str: "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        default_bool: None,
        env_var: Some("PADDLEOCR_JOB_URL"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "paddleocr_model",
        nested_vault_config: false,
        value_type: "string",
        default_str: "PaddleOCR-VL-1.6",
        default_bool: None,
        env_var: Some("PADDLEOCR_MODEL"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "embedding_profile",
        nested_vault_config: false,
        value_type: "string",
        default_str: "default",
        default_bool: None,
        env_var: Some("PAPERFORGE_EMBEDDING_PROFILE"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "vector_db_provider_type",
        nested_vault_config: false,
        value_type: "enum",
        default_str: "openai_sdk",
        default_bool: None,
        env_var: Some("VECTOR_DB_PROVIDER_TYPE"),
        choices: PROVIDER_TYPES,
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "vector_db_api_base",
        nested_vault_config: false,
        value_type: "string",
        default_str: "",
        default_bool: None,
        env_var: Some("VECTOR_DB_API_BASE"),
        choices: &[],
        writable: true,
        allow_empty: true,
        vault_relative: false,
    },
    FieldSpec {
        key: "vector_db_api_model",
        nested_vault_config: false,
        value_type: "string",
        default_str: "text-embedding-3-small",
        default_bool: None,
        env_var: Some("VECTOR_DB_API_MODEL"),
        choices: &[],
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "vector_db_dimensions",
        nested_vault_config: false,
        value_type: "string",
        default_str: "",
        default_bool: None,
        env_var: Some("VECTOR_DB_DIMENSIONS"),
        choices: &[],
        writable: true,
        allow_empty: true,
        vault_relative: false,
    },
    FieldSpec {
        key: "zotero_source_mode",
        nested_vault_config: false,
        value_type: "enum",
        default_str: "sqlite",
        default_bool: None,
        env_var: Some("PAPERFORGE_ZOTERO_SOURCE_MODE"),
        choices: ZOTERO_SOURCE_MODES,
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "domain_mode",
        nested_vault_config: false,
        value_type: "enum",
        default_str: "per_collection",
        default_bool: None,
        env_var: Some("PAPERFORGE_DOMAIN_MODE"),
        choices: DOMAIN_MODES,
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
    FieldSpec {
        key: "zotero_selected_collections",
        nested_vault_config: false,
        value_type: "string",
        default_str: "",
        default_bool: None,
        env_var: Some("PAPERFORGE_ZOTERO_COLLECTIONS"),
        choices: &[],
        writable: true,
        allow_empty: true,
        vault_relative: false,
    },
    FieldSpec {
        key: "journal_metrics_mode",
        nested_vault_config: false,
        value_type: "enum",
        default_str: "auto",
        default_bool: None,
        env_var: Some("PAPERFORGE_JOURNAL_METRICS_MODE"),
        choices: JOURNAL_METRICS_MODES,
        writable: true,
        allow_empty: false,
        vault_relative: false,
    },
];

const LEGACY_TOP_PATH_KEYS: &[&str] = &[
    "system_dir",
    "resources_dir",
    "literature_dir",
    "control_dir",
    "base_dir",
    "skill_dir",
    "command_dir",
];

const SECRET_SUBSTRINGS: &[&str] = &["api_key", "api_token", "token", "password", "secret"];

pub fn is_secret_like(key: &str) -> bool {
    let lower = key.to_ascii_lowercase();
    SECRET_SUBSTRINGS.iter().any(|p| lower.contains(p))
}

pub fn pf_ok(command: &str, data: Value) -> Value {
    json!({
        "ok": true,
        "command": command,
        "version": PF_VERSION,
        "data": data,
        "error": Value::Null,
    })
}

pub fn pf_err(command: &str, code: &str, message: &str, details: Value, suggestions: &[&str]) -> Value {
    let mut err_obj = Map::new();
    err_obj.insert("code".into(), json!(code));
    err_obj.insert("message".into(), json!(message));
    err_obj.insert("details".into(), details);
    if !suggestions.is_empty() {
        err_obj.insert("suggestions".into(), json!(suggestions));
    }
    json!({
        "ok": false,
        "command": command,
        "version": PF_VERSION,
        "data": Value::Null,
        "error": Value::Object(err_obj),
    })
}

pub fn expand_tilde(raw: &str) -> PathBuf {
    if raw == "~" || raw.starts_with("~/") || raw.starts_with("~\\") {
        let home = env::var("HOME")
            .or_else(|_| env::var("USERPROFILE"))
            .unwrap_or_default();
        if !home.is_empty() {
            if raw == "~" {
                return PathBuf::from(home);
            }
            return PathBuf::from(home).join(&raw[2..]);
        }
    }
    PathBuf::from(raw)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

pub struct LoadedConfig {
    pub doc: Map<String, Value>,
    pub revision: String,
    pub unknown_keys: Vec<String>,
}

#[derive(Debug)]
pub enum ConfigIssue {
    NotFound(String),
    Corrupt(String),
    MigrationRequired(Vec<String>),
    FutureSchema(i64),
    SecretField(String),
    Invalid(String, String),
}

impl ConfigIssue {
    pub fn code(&self) -> &'static str {
        match self {
            ConfigIssue::NotFound(_) => "config.not_found",
            ConfigIssue::Corrupt(_) => "config.corrupt",
            ConfigIssue::MigrationRequired(_) => "config.migration_required",
            ConfigIssue::FutureSchema(_) => "config.future_schema",
            ConfigIssue::SecretField(_) => "config.secret_field",
            ConfigIssue::Invalid(_, _) => "config.invalid",
        }
    }

    pub fn to_pf_error(&self, command: &str) -> Value {
        let c = self.code();
        let (details, suggestions): (Value, &[&str]) = match self {
            ConfigIssue::NotFound(p) => (
                json!({"config_code": c, "path": p}),
                &["run 'paperforge config init' or 'paperforge setup'"],
            ),
            ConfigIssue::Corrupt(p) => (json!({"config_code": c, "path": p}), &[]),
            ConfigIssue::MigrationRequired(keys) => (
                json!({"config_code": c, "legacy_keys": keys}),
                &["run 'paperforge config migrate --dry-run' to preview"],
            ),
            ConfigIssue::FutureSchema(sv) => (json!({"config_code": c, "schema_version": sv}), &[]),
            ConfigIssue::SecretField(k) => (json!({"config_code": c, "key": k}), &[]),
            ConfigIssue::Invalid(k, r) => (json!({"config_code": c, "key": k, "reason": r}), &[]),
        };
        pf_err(command, "validation_error", c, details, suggestions)
    }
}

fn spec_default_value(spec: &FieldSpec) -> Value {
    if let Some(b) = spec.default_bool {
        Value::Bool(b)
    } else {
        Value::String(spec.default_str.to_string())
    }
}

pub fn validate_scalar(spec: &FieldSpec, val: &Value) -> Result<Value, String> {
    match spec.value_type {
        "boolean" => match val {
            Value::Bool(b) => Ok(Value::Bool(*b)),
            Value::String(s) => match s.trim().to_ascii_lowercase().as_str() {
                "true" | "1" | "yes" | "on" => Ok(Value::Bool(true)),
                "false" | "0" | "no" | "off" => Ok(Value::Bool(false)),
                _ => Err("expected boolean".into()),
            },
            _ => Err("expected boolean".into()),
        },
        "enum" => {
            let s = val.as_str().ok_or_else(|| "expected string".to_string())?.trim();
            if !spec.choices.contains(&s) {
                return Err(format!("must be one of {:?}", spec.choices));
            }
            Ok(Value::String(s.to_string()))
        }
        "path" => {
            let s = val.as_str().ok_or_else(|| "expected path string".to_string())?.trim();
            if s.is_empty() && !spec.allow_empty {
                return Err("must not be empty".into());
            }
            if spec.vault_relative && !s.is_empty() {
                let p = Path::new(s);
                if p.is_absolute() || s.split(['/', '\\']).any(|seg| seg == "..") {
                    return Err("vault-relative path cannot be absolute or contain '..'".into());
                }
            }
            Ok(Value::String(s.to_string()))
        }
        _ => {
            let s = val.as_str().ok_or_else(|| "expected string".to_string())?.trim();
            if s.is_empty() && !spec.allow_empty {
                return Err("must not be empty".into());
            }
            Ok(Value::String(s.to_string()))
        }
    }
}

pub fn load_canonical_config(vault: &Path) -> Result<LoadedConfig, ConfigIssue> {
    let cfg_path = vault.join(CONFIG_FILE);
    if !cfg_path.exists() {
        return Err(ConfigIssue::NotFound(cfg_path.to_string_lossy().into_owned()));
    }
    let raw = fs::read(&cfg_path).map_err(|_| ConfigIssue::Corrupt(cfg_path.to_string_lossy().into_owned()))?;
    let parsed: Value =
        serde_json::from_slice(&raw).map_err(|_| ConfigIssue::Corrupt(cfg_path.to_string_lossy().into_owned()))?;
    let obj = parsed
        .as_object()
        .ok_or_else(|| ConfigIssue::Corrupt(cfg_path.to_string_lossy().into_owned()))?;

    for k in obj.keys() {
        if k != "vault_config" && is_secret_like(k) {
            return Err(ConfigIssue::SecretField(k.clone()));
        }
    }
    if let Some(vc) = obj.get("vault_config").and_then(|v| v.as_object()) {
        for k in vc.keys() {
            if is_secret_like(k) {
                return Err(ConfigIssue::SecretField(format!("vault_config.{k}")));
            }
        }
    }

    let mut legacy_hits = Vec::new();
    for &lk in LEGACY_TOP_PATH_KEYS {
        if obj.contains_key(lk) {
            legacy_hits.push(lk.to_string());
        }
    }
    for &dk in &["agent_key", "paperforge_path", "zotero_link"] {
        if obj.contains_key(dk) {
            legacy_hits.push(dk.to_string());
        }
    }
    let sv = obj.get("schema_version").and_then(|v| v.as_i64());
    match sv {
        None | Some(1) => {
            legacy_hits.push("schema_version".into());
            return Err(ConfigIssue::MigrationRequired(legacy_hits));
        }
        Some(v) if v > SCHEMA_VERSION => return Err(ConfigIssue::FutureSchema(v)),
        Some(v) if v != SCHEMA_VERSION => {
            return Err(ConfigIssue::Invalid(
                "schema_version".into(),
                format!("unsupported schema_version {v}"),
            ))
        }
        Some(_) => {}
    }
    if !legacy_hits.is_empty() {
        return Err(ConfigIssue::MigrationRequired(legacy_hits));
    }

    if let Some(vc_val) = obj.get("vault_config") {
        if !vc_val.is_object() {
            return Err(ConfigIssue::Invalid(
                "vault_config".into(),
                "must be an object".into(),
            ));
        }
    }

    // Validate stored known fields & collect unknown keys
    let mut unknown = Vec::new();
    for (k, v) in obj {
        if k == "schema_version" || k == "vault_config" {
            continue;
        }
        if let Some(spec) = FIELD_SPECS.iter().find(|s| !s.nested_vault_config && s.key == k) {
            if !v.is_null() {
                validate_scalar(spec, v).map_err(|r| ConfigIssue::Invalid(k.clone(), r))?;
            }
        } else {
            unknown.push(k.clone());
        }
    }
    if let Some(vc) = obj.get("vault_config").and_then(|v| v.as_object()) {
        for (k, v) in vc {
            if let Some(spec) = FIELD_SPECS.iter().find(|s| s.nested_vault_config && s.key == k) {
                if !v.is_null() {
                    validate_scalar(spec, v)
                        .map_err(|r| ConfigIssue::Invalid(format!("vault_config.{k}"), r))?;
                }
            } else {
                unknown.push(format!("vault_config.{k}"));
            }
        }
    }
    unknown.sort();

    Ok(LoadedConfig {
        doc: obj.clone(),
        revision: format!("sha256:{}", sha256_hex(&raw)),
        unknown_keys: unknown,
    })
}

pub fn resolve_field_payload(doc: &Map<String, Value>, spec: &FieldSpec) -> Value {
    let stored_opt = if spec.nested_vault_config {
        doc.get("vault_config")
            .and_then(|v| v.as_object())
            .and_then(|vc| vc.get(spec.key))
            .filter(|v| !v.is_null())
    } else {
        doc.get(spec.key).filter(|v| !v.is_null())
    };

    let stored_val = stored_opt
        .and_then(|v| validate_scalar(spec, v).ok());
    let is_set = stored_val.is_some();

    let env_val = spec.env_var.and_then(|ename| {
        env::var(ename)
            .ok()
            .filter(|s| !s.trim().is_empty())
            .and_then(|s| validate_scalar(spec, &Value::String(s)).ok())
    });

    let (effective, source) = if let Some(ev) = env_val {
        (ev, "environment")
    } else if let Some(ref sv) = stored_val {
        (sv.clone(), "file")
    } else {
        (spec_default_value(spec), "default")
    };

    json!({
        "key": spec.key,
        "value": effective,
        "stored_value": stored_val.unwrap_or(Value::Null),
        "source": source,
        "is_set": is_set,
        "type": spec.value_type,
        "default": spec_default_value(spec),
        "environment": spec.env_var,
        "choices": spec.choices,
        "writable": spec.writable,
        "allow_empty": spec.allow_empty,
        "vault_relative": spec.vault_relative,
    })
}

pub fn resolve_vault_paths(vault: &Path, doc: &Map<String, Value>) -> Map<String, Value> {
    let get_str = |key: &str| -> String {
        let spec = FIELD_SPECS.iter().find(|s| s.key == key).unwrap();
        resolve_field_payload(doc, spec)["value"]
            .as_str()
            .unwrap_or(spec.default_str)
            .to_string()
    };

    let vault_abs = fs::canonicalize(vault).unwrap_or_else(|_| vault.to_path_buf());
    // Strip Windows UNC `\\?\` prefix produced by `fs::canonicalize`
    let clean_vault = strip_verbatim_prefix(&vault_abs);

    let sys_rel = get_str("system_dir");
    let system = clean_vault.join(&sys_rel);
    let paperforge = if Path::new(&sys_rel)
        .file_name()
        .and_then(|n| n.to_str())
        == Some(".paperforge")
    {
        system.clone()
    } else {
        system.join("PaperForge")
    };

    let resources = clean_vault.join(get_str("resources_dir"));
    let literature = resources.join(get_str("literature_dir"));
    let control = resources.join(get_str("control_dir"));
    let bases = clean_vault.join(get_str("base_dir"));
    let skill_dir = clean_vault.join(get_str("skill_dir"));

    let zot_raw = get_str("zotero_data_dir");
    let zotero_dir = if zot_raw.trim().is_empty() {
        system.join("Zotero")
    } else {
        let zp = expand_tilde(zot_raw.trim());
        if zp.is_absolute() {
            zp
        } else {
            clean_vault.join(zp)
        }
    };

    let pf_deep_script = skill_dir
        .join("paperforge")
        .join("scripts")
        .join("pf_deep.py");

    let mut m = Map::new();
    let mut ins = |k: &str, p: PathBuf| {
        m.insert(k.to_string(), Value::String(p.to_string_lossy().into_owned()));
    };
    ins("vault", clean_vault);
    ins("system", system);
    ins("paperforge", paperforge.clone());
    ins("exports", paperforge.join("exports"));
    ins("ocr", paperforge.join("ocr"));
    ins("zotero_dir", zotero_dir);
    ins("resources", resources);
    ins("literature", literature);
    ins("control", control.clone());
    ins("library_records", control.join("library-records"));
    ins("bases", bases);
    ins("worker_script", paperforge.join("worker"));
    ins("skill_dir", skill_dir);
    ins("pf_deep_script", pf_deep_script);
    ins("config", paperforge.join("config").join("domain-collections.json"));
    ins("index", paperforge.join("indexes").join("formal-library.json"));
    m
}

pub fn strip_verbatim_prefix(p: &Path) -> PathBuf {
    let s = p.to_string_lossy();
    if let Some(stripped) = s.strip_prefix(r"\\?\") {
        PathBuf::from(stripped)
    } else {
        p.to_path_buf()
    }
}

/// Handle `config <verb> ...` natively when `--json` is passed.
/// Returns `Some((exit_code, stdout, stderr))` if handled natively, or `None` to delegate.
pub fn try_handle_config_cli(vault: &Path, argv: &[String]) -> Option<(i32, String, String)> {
    let is_json = argv.iter().any(|a| a == "--json");
    if argv.first().map(|s| s.as_str()) == Some("paths") && is_json {
        return match load_canonical_config(vault) {
            Ok(cfg) => {
                let paths = resolve_vault_paths(vault, &cfg.doc);
                let out = pf_ok("paths", Value::Object(paths));
                Some((0, format!("{out}\n"), String::new()))
            }
            Err(issue) => {
                let out = issue.to_pf_error("paths");
                Some((1, format!("{out}\n"), String::new()))
            }
        };
    }

    if argv.first().map(|s| s.as_str()) != Some("config") || !is_json {
        return None;
    }

    let positional: Vec<&str> = argv[1..]
        .iter()
        .filter(|a| !a.starts_with('-'))
        .map(|s| s.as_str())
        .collect();
    let verb = *positional.first()?;

    match verb {
        "list" => match load_canonical_config(vault) {
            Ok(cfg) => {
                let fields: Vec<Value> = FIELD_SPECS
                    .iter()
                    .map(|s| resolve_field_payload(&cfg.doc, s))
                    .collect();
                let out = pf_ok(
                    "config.list",
                    json!({
                        "schema_version": SCHEMA_VERSION,
                        "revision": cfg.revision,
                        "unknown_keys": cfg.unknown_keys,
                        "fields": fields,
                    }),
                );
                Some((0, format!("{out}\n"), String::new()))
            }
            Err(issue) => Some((1, format!("{}\n", issue.to_pf_error("config.list")), String::new())),
        },
        "get" => {
            let Some(&key) = positional.get(1) else {
                let out = pf_err("config.get", "validation_error", "config.usage", json!({"verb": "get"}), &[]);
                return Some((2, format!("{out}\n"), String::new()));
            };
            match load_canonical_config(vault) {
                Ok(cfg) => {
                    let Some(spec) = FIELD_SPECS.iter().find(|s| s.key == key) else {
                        let out = pf_err(
                            "config.get",
                            "validation_error",
                            "config.unknown_key",
                            json!({"config_code": "config.unknown_key", "key": key}),
                            &[],
                        );
                        return Some((2, format!("{out}\n"), String::new()));
                    };
                    let out = pf_ok(
                        "config.get",
                        json!({
                            "schema_version": SCHEMA_VERSION,
                            "revision": cfg.revision,
                            "unknown_keys": cfg.unknown_keys,
                            "field": resolve_field_payload(&cfg.doc, spec),
                        }),
                    );
                    Some((0, format!("{out}\n"), String::new()))
                }
                Err(issue) => Some((1, format!("{}\n", issue.to_pf_error("config.get")), String::new())),
            }
        }
        "paths" => match load_canonical_config(vault) {
            Ok(cfg) => {
                let paths = resolve_vault_paths(vault, &cfg.doc);
                let out = pf_ok(
                    "config.paths",
                    json!({
                        "schema_version": SCHEMA_VERSION,
                        "revision": cfg.revision,
                        "paths": paths,
                    }),
                );
                Some((0, format!("{out}\n"), String::new()))
            }
            Err(issue) => Some((1, format!("{}\n", issue.to_pf_error("config.paths")), String::new())),
        },
        "validate" => {
            let out = match load_canonical_config(vault) {
                Ok(cfg) => pf_ok(
                    "config.validate",
                    json!({
                        "state": "valid",
                        "revision": cfg.revision,
                        "errors": [],
                        "warnings": [],
                        "migration": Value::Null,
                    }),
                ),
                Err(ConfigIssue::NotFound(_)) => pf_ok(
                    "config.validate",
                    json!({
                        "state": "missing",
                        "revision": Value::Null,
                        "errors": [{"code": "config.not_found"}],
                        "warnings": [],
                        "migration": Value::Null,
                    }),
                ),
                Err(ConfigIssue::MigrationRequired(keys)) => pf_ok(
                    "config.validate",
                    json!({
                        "state": "migration_required",
                        "revision": Value::Null,
                        "errors": [{"code": "config.migration_required", "legacy_keys": keys}],
                        "warnings": [],
                        "migration": {"required": true, "legacy_keys": keys},
                    }),
                ),
                Err(ConfigIssue::FutureSchema(sv)) => pf_ok(
                    "config.validate",
                    json!({
                        "state": "future_schema",
                        "revision": Value::Null,
                        "errors": [{"code": "config.future_schema", "schema_version": sv}],
                        "warnings": [],
                        "migration": Value::Null,
                    }),
                ),
                Err(other) => pf_ok(
                    "config.validate",
                    json!({
                        "state": "invalid",
                        "revision": Value::Null,
                        "errors": [{"code": other.code()}],
                        "warnings": [],
                        "migration": Value::Null,
                    }),
                ),
            };
            Some((0, format!("{out}\n"), String::new()))
        }
        "set" => {
            let (Some(&key), Some(&raw_val)) = (positional.get(1), positional.get(2)) else {
                let out = pf_err("config.set", "validation_error", "config.usage", json!({"verb": "set"}), &[]);
                return Some((2, format!("{out}\n"), String::new()));
            };
            if is_secret_like(key) {
                let out = ConfigIssue::SecretField(key.into()).to_pf_error("config.set");
                return Some((2, format!("{out}\n"), String::new()));
            }
            let Some(spec) = FIELD_SPECS.iter().find(|s| s.key == key) else {
                let out = pf_err(
                    "config.set",
                    "validation_error",
                    "config.unknown_key",
                    json!({"config_code": "config.unknown_key", "key": key}),
                    &[],
                );
                return Some((2, format!("{out}\n"), String::new()));
            };
            let parsed = match validate_scalar(spec, &Value::String(raw_val.to_string())) {
                Ok(v) => v,
                Err(reason) => {
                    let out = ConfigIssue::Invalid(key.into(), reason).to_pf_error("config.set");
                    return Some((1, format!("{out}\n"), String::new()));
                }
            };
            match load_canonical_config(vault) {
                Ok(mut cfg) => {
                    let changed = if spec.nested_vault_config {
                        let vc = cfg
                            .doc
                            .entry("vault_config")
                            .or_insert_with(|| json!({}))
                            .as_object_mut()
                            .unwrap();
                        let same = vc.get(key) == Some(&parsed);
                        if !same {
                            vc.insert(key.to_string(), parsed);
                        }
                        !same
                    } else {
                        let same = cfg.doc.get(key) == Some(&parsed);
                        if !same {
                            cfg.doc.insert(key.to_string(), parsed);
                        }
                        !same
                    };
                    if changed {
                        let mut bytes = serde_json::to_vec_pretty(&Value::Object(cfg.doc)).unwrap();
                        bytes.push(b'\n');
                        if let Err(e) = atomic_write_bytes(&vault.join(CONFIG_FILE), &bytes) {
                            let out = pf_err("config.set", "io_error", &e.to_string(), json!({}), &[]);
                            return Some((1, format!("{out}\n"), String::new()));
                        }
                    }
                    let reloaded = load_canonical_config(vault).unwrap();
                    let out = pf_ok(
                        "config.set",
                        json!({
                            "schema_version": SCHEMA_VERSION,
                            "revision": reloaded.revision,
                            "unknown_keys": reloaded.unknown_keys,
                            "changed": changed,
                            "field": resolve_field_payload(&reloaded.doc, spec),
                        }),
                    );
                    Some((0, format!("{out}\n"), String::new()))
                }
                Err(issue) => Some((1, format!("{}\n", issue.to_pf_error("config.set")), String::new())),
            }
        }
        "unset" => {
            let Some(&key) = positional.get(1) else {
                let out = pf_err("config.unset", "validation_error", "config.usage", json!({"verb": "unset"}), &[]);
                return Some((2, format!("{out}\n"), String::new()));
            };
            if is_secret_like(key) {
                let out = ConfigIssue::SecretField(key.into()).to_pf_error("config.unset");
                return Some((2, format!("{out}\n"), String::new()));
            }
            let Some(spec) = FIELD_SPECS.iter().find(|s| s.key == key) else {
                let out = pf_err(
                    "config.unset",
                    "validation_error",
                    "config.unknown_key",
                    json!({"config_code": "config.unknown_key", "key": key}),
                    &[],
                );
                return Some((2, format!("{out}\n"), String::new()));
            };
            match load_canonical_config(vault) {
                Ok(mut cfg) => {
                    let changed = if spec.nested_vault_config {
                        cfg.doc
                            .get_mut("vault_config")
                            .and_then(|v| v.as_object_mut())
                            .and_then(|vc| vc.remove(key))
                            .is_some()
                    } else {
                        cfg.doc.remove(key).is_some()
                    };
                    if changed {
                        let mut bytes = serde_json::to_vec_pretty(&Value::Object(cfg.doc)).unwrap();
                        bytes.push(b'\n');
                        if let Err(e) = atomic_write_bytes(&vault.join(CONFIG_FILE), &bytes) {
                            let out = pf_err("config.unset", "io_error", &e.to_string(), json!({}), &[]);
                            return Some((1, format!("{out}\n"), String::new()));
                        }
                    }
                    let reloaded = load_canonical_config(vault).unwrap();
                    let out = pf_ok(
                        "config.unset",
                        json!({
                            "schema_version": SCHEMA_VERSION,
                            "revision": reloaded.revision,
                            "unknown_keys": reloaded.unknown_keys,
                            "changed": changed,
                            "field": resolve_field_payload(&reloaded.doc, spec),
                        }),
                    );
                    Some((0, format!("{out}\n"), String::new()))
                }
                Err(issue) => Some((1, format!("{}\n", issue.to_pf_error("config.unset")), String::new())),
            }
        }
        "init" => {
            if !vault.exists() {
                let out = ConfigIssue::NotFound(vault.to_string_lossy().into_owned()).to_pf_error("config.init");
                return Some((1, format!("{out}\n"), String::new()));
            }
            let cfg_file = vault.join(CONFIG_FILE);
            if cfg_file.exists() {
                match load_canonical_config(vault) {
                    Ok(cfg) => {
                        let fields: Vec<Value> = FIELD_SPECS
                            .iter()
                            .map(|s| resolve_field_payload(&cfg.doc, s))
                            .collect();
                        let out = pf_ok(
                            "config.init",
                            json!({
                                "schema_version": SCHEMA_VERSION,
                                "revision": cfg.revision,
                                "unknown_keys": cfg.unknown_keys,
                                "changed": false,
                                "fields": fields,
                            }),
                        );
                        return Some((0, format!("{out}\n"), String::new()));
                    }
                    Err(issue) => return Some((1, format!("{}\n", issue.to_pf_error("config.init")), String::new())),
                }
            }
            let mut vc = Map::new();
            let mut doc = Map::new();
            doc.insert("schema_version".into(), json!(SCHEMA_VERSION));
            for spec in FIELD_SPECS {
                if spec.nested_vault_config {
                    vc.insert(spec.key.into(), spec_default_value(spec));
                } else {
                    doc.insert(spec.key.into(), spec_default_value(spec));
                }
            }
            doc.insert("vault_config".into(), Value::Object(vc));
            let mut bytes = serde_json::to_vec_pretty(&Value::Object(doc)).unwrap();
            bytes.push(b'\n');
            if let Err(e) = atomic_write_bytes(&cfg_file, &bytes) {
                let out = pf_err("config.init", "io_error", &e.to_string(), json!({}), &[]);
                return Some((1, format!("{out}\n"), String::new()));
            }
            let reloaded = load_canonical_config(vault).unwrap();
            let fields: Vec<Value> = FIELD_SPECS
                .iter()
                .map(|s| resolve_field_payload(&reloaded.doc, s))
                .collect();
            let out = pf_ok(
                "config.init",
                json!({
                    "schema_version": SCHEMA_VERSION,
                    "revision": reloaded.revision,
                    "unknown_keys": reloaded.unknown_keys,
                    "changed": true,
                    "fields": fields,
                }),
            );
            Some((0, format!("{out}\n"), String::new()))
        }
        _ => None, // `config migrate` delegates to Python if available
    }
}
