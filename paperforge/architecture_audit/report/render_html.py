"""Self-contained architecture report HTML projection (#134).

Consumes DeterministicAudit plus optional ArchitectureReview through read-only
composition — never mutates, reclassifies, or persists canonical facts.

Views: Overview, Asset Groups / Publication Units, Operations, Signals,
Interfaces / Authorities, Findings, Evidence / Unresolved. Deterministic and
review layers have separate visual labels and provenance. The HTML is
self-contained, performs no network request, is regenerable from the input
JSONs, and is never committed as architecture truth.

Design contract: quiet professional, progressive clarity, semantic text plus
color, borders-only depth, keyboard access, visible focus, reduced motion,
responsive layouts.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

SEVERITY_COLOR = {"blocking": "#dc2626", "advisory": "#d97706", "informational": "#2563eb"}
STATUS_LABEL = {
    "satisfied": ("✓ satisfied", "#16a34a"),
    "violated": ("✗ violated", "#dc2626"),
    "planned_gap": ("⏳ planned gap", "#2563eb"),
    "exception_applied": ("ⓘ exception", "#7c3aed"),
    "unresolved": ("? unresolved", "#d97706"),
    "not_evaluated": ("— not evaluated", "#6b7280"),
}
COVERAGE_COLOR = {
    "complete": "#16a34a",
    "partial": "#d97706",
    "unavailable": "#d97706",
    "failed": "#dc2626",
}


def _esc(value: Any) -> str:
    """Safe escaping for any user-controlled text."""
    return html.escape(str(value))


class ReportData:
    """Loads and validates the input JSON set (all optional except audit)."""

    def __init__(self, audit: dict[str, Any], survey: dict[str, Any] | None = None,
                 review: dict[str, Any] | None = None, contract: dict[str, Any] | None = None,
                 summary: dict[str, Any] | None = None, traces: list[dict[str, Any]] | None = None):
        self.audit = audit
        self.survey = survey or {}
        self.review = review or {}
        self.contract = contract or {}
        self.summary = summary or {}
        self.traces = traces or []

    @classmethod
    def from_dir(cls, directory: Path) -> ReportData:
        def load(name: str) -> Any:
            path = directory / name
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        audit = load("audit.json")
        if audit is None:
            raise ValueError(f"audit.json missing in {directory}")
        return cls(
            audit=audit,
            survey=load("survey.json"),
            review=load("review.json"),
            contract=load("contract.json"),
            summary=load("summary.json"),
            traces=load("traces.json"),
        )


def _assessment(data: ReportData) -> dict[str, Any]:
    return data.audit.get("content", {}).get("assessment", {})


def _findings(data: ReportData) -> list[dict[str, Any]]:
    return list(data.audit.get("content", {}).get("findings", []))


def _badge(text: str, color: str) -> str:
    return f"<span class='badge' style='color:{color};border-color:{color}'>{text}</span>"


def _evidence_html(ev: dict[str, Any]) -> str:
    file = _esc(ev.get("file", ""))
    symbol = _esc(ev.get("symbol", ""))
    start, end = ev.get("line_start", 0), ev.get("line_end", 0)
    extractor = _esc(ev.get("extractor", ""))
    eid = _esc(ev.get("evidence_id", ""))
    digest = _esc(ev.get("file_digest", ""))
    copy_payload = json.dumps({
        "file": file, "symbol": symbol, "lines": f"{start}-{end}",
        "extractor": extractor, "evidence_id": eid, "file_digest": digest,
    })
    return (
        f"<div class='ev'><code>{file}</code> · {symbol} : {start}–{end}"
        f"<span class='tag'>{extractor}</span>"
        f"<button type='button' class='copy-btn' data-copy='{_esc(copy_payload)}' "
        f"aria-label='copy evidence'>⧉</button>"
        f"<div class='digest'>{eid} · {digest}</div></div>"
    )


def banner(data: ReportData) -> str:
    assessment = _assessment(data)
    status = assessment.get("status", "unknown")
    gate = assessment.get("gate_eligible", False)
    color = {"clean": "#16a34a", "findings": "#fbbf24", "incomplete": "#d97706", "failed": "#dc2626"}.get(status, "#94a3b8")
    findings = _findings(data)
    counts = {s: sum(1 for f in findings if f.get("rule_status") == s) for s in STATUS_LABEL}
    reasons = " · ".join(_esc(r) for r in assessment.get("reasons", [])) or "—"
    return f"""
    <div class="banner">
      <span class="big" style="color:{color}">{_esc(status)}</span>
      <span class="sub">确定性评估 · {len(findings)} 条发现
      （{counts.get('unresolved', 0)} unresolved · {counts.get('violated', 0)} violated ·
       {counts.get('planned_gap', 0)} planned gap · {counts.get('satisfied', 0)} satisfied）
      <br>gate_eligible: {gate} · 原因：{reasons}</span>
    </div>"""


def meta_row(data: ReportData) -> str:
    content = data.audit.get("content", {})
    spans = [
        ("audit", content.get("bound_contract_digest", "")),
        ("contract", content.get("bound_contract_digest", "")),
        ("survey", content.get("bound_survey_digest", "")),
        ("reconciler", content.get("reconciler_version", "")),
    ]
    survey = data.survey
    repo_state = survey.get("repository_state", {}) if survey else {}
    out = []
    if repo_state:
        out.append(f"<span>revision <b>{_esc(repo_state.get('revision', ''))}</b></span>")
        out.append(f"<span>dirty <b>{_esc(repo_state.get('dirty'))}</b></span>")
        if repo_state.get("dirty_diff_digest"):
            out.append(f"<span>diff <span class='digest'>{_esc(repo_state['dirty_diff_digest'])}</span></span>")
    for label, value in spans:
        out.append(f"<span>{label} <span class='digest'>{_esc(value)}</span></span>")
    return "".join(out)


def layers_row(data: ReportData) -> str:
    assessment = _assessment(data)
    rows = [
        ("ArchitectureContract", "声明意图：规则、发布单元、生命周期", f"{len(data.contract.get('rules', []))} rules"),
        ("ArchitectureSurvey", "确定性观察：证据 + digest", f"extractors {len(data.survey.get('coverage', []))}"),
        ("DeterministicAudit", "纯 reconciliation：rule_status + assessment", assessment.get("status", "—")),
        ("ArchitectureReview", "维护者注解层（inferred/unresolved）", data.review.get("reviewer_type", "—")),
        ("ArchitectureReportView", "只读组合投影（本页）", "review bound ✓" if data.review else "no review"),
    ]
    return "".join(
        f"<div class='layer-card'><div class='layer-name'>{name}</div>"
        f"<div class='layer-desc'>{desc}</div><div><span class='badge'>{state}</span></div></div>"
        for name, desc, state in rows
    )


def assets_row(data: ReportData) -> str:
    units = data.contract.get("publication_units", [])
    groups: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        groups.setdefault(unit.get("asset_group", "?"), []).append(unit)
    out = []
    for group, group_units in sorted(groups.items()):
        unit_text = "；".join(
            f"<code>{_esc(u.get('unit_id', ''))}</code>"
            f"<span class='sub'>← {_esc(u.get('publication_authority', ''))}</span>"
            for u in group_units
        ) or "—"
        out.append(
            f"<div class='asset-card'><span class='badge'>{_esc(group)}</span>"
            f"<div class='unit'>{unit_text}</div></div>"
        )
    return "".join(out)


def operations_row(data: ReportData) -> str:
    ops = data.contract.get("operations", [])
    facts = data.survey.get("facts", [])
    out = []
    for op in ops:
        op_id = op.get("operation_id", op) if isinstance(op, dict) else op
        relevant = [
            f for f in facts
            if f.get("operation_id") == op_id
            or (f.get("evidence") or {}).get("file", "")
            .split("/")[-1].removesuffix(".py") == op_id
        ]
        kinds: dict[str, int] = {}
        for f in relevant:
            kind = f.get("kind", "?")
            kinds[kind] = kinds.get(kind, 0) + 1
        kind_text = " · ".join(f"{k}:{n}" for k, n in sorted(kinds.items())) or "—"
        out.append(
            f"<div class='asset-card'><span class='badge'>{_esc(op_id)}</span>"
            f"<div class='sub'>facts: {kind_text}</div></div>"
        )
    return "".join(out)


def signals_row(data: ReportData) -> str:
    facts = [
        f for f in data.survey.get("facts", [])
        if f.get("kind") == "signal"
    ]
    rows = []
    for f in facts:
        ev = f.get("evidence") or {}
        rows.append(
            f"<tr><td><code>{_esc(f.get('signal_id', ''))}</code></td>"
            f"<td><code>{_esc(f.get('producer', ''))}</code></td>"
            f"<td>{_esc(f.get('consumer_kind', ''))}</td>"
            f"<td>{_esc(f.get('consumer', '')) or '—'}</td>"
            f"<td>{'code' if f.get('has_code_consumer') else '—'}</td>"
            f"<td><code>{_esc(ev.get('file', ''))}</code> : {_esc(ev.get('line_start', ''))}</td></tr>"
        )
    return "".join(rows)


def findings_table(data: ReportData, filter_status: str = "all") -> str:
    rows = []
    for f in _findings(data):
        status = f.get("rule_status", "not_evaluated")
        if filter_status != "all" and status != filter_status:
            continue
        label, color = STATUS_LABEL.get(status, (status, "#6b7280"))
        sev = SEVERITY_COLOR.get(f.get("severity", ""), "#6b7280")
        ev_html = "".join(_evidence_html(e) for e in f.get("evidence", []))
        rows.append(
            f"<tr><td><code>{_esc(f.get('rule_id', ''))}</code>"
            f"<div class='sub'>{_esc(f.get('subject', '') or '—')}</div>"
            f"<div class='sub digest'>{_esc(f.get('finding_id', ''))}</div></td>"
            f"<td>{_badge(label, color)}</td>"
            f"<td>{_badge(_esc(f.get('severity', '')), sev)}</td>"
            f"<td>{_esc(f.get('message', ''))}{ev_html}</td></tr>"
        )
    if not rows:
        return "<tr><td colspan='4' class='sub'>无匹配发现</td></tr>"
    return "".join(rows)


def coverage_table(data: ReportData) -> str:
    rows = []
    required = set(data.contract.get("required_extractors", []))
    for c in data.audit.get("content", {}).get("coverage", []):
        state = c.get("status", "unavailable")
        color = COVERAGE_COLOR.get(state, "#6b7280")
        rows.append(
            f"<tr><td><code>{_esc(c.get('extractor', ''))}</code></td>"
            f"<td>{_badge(_esc(state), color)}</td>"
            f"<td>{'required' if c.get('extractor') in required else 'optional'}</td>"
            f"<td>{_esc('；'.join(c.get('diagnostics', [])))}</td></tr>"
        )
    return "".join(rows)


def review_table(data: ReportData) -> str:
    rows = []
    for a in data.review.get("adjudications", []):
        rows.append(
            f"<tr><td><code>{_esc(a.get('finding_id', ''))}</code></td>"
            f"<td>{_badge(_esc(a.get('adjudication', '')), '#7c3aed')}</td>"
            f"<td>{_esc(a.get('rationale', ''))}</td>"
            f"<td><span class='badge'>{_esc(a.get('epistemic_status', ''))}</span></td></tr>"
        )
    for s in data.review.get("semantic_findings", []):
        rows.append(
            f"<tr><td><code>{_esc(s.get('finding_id', ''))}</code></td>"
            f"<td>{_badge('semantic finding', '#7c3aed')}</td>"
            f"<td>{_esc(s.get('message', ''))}</td>"
            f"<td><span class='badge'>{_esc(s.get('epistemic_status', ''))}</span></td></tr>"
        )
    for r in data.review.get("evidence_requests", []):
        rows.append(
            f"<tr><td><code>{_esc(r.get('request_id', ''))}</code></td>"
            f"<td>{_badge('evidence request', '#d97706')}</td>"
            f"<td><b>{_esc(r.get('subject', ''))}</b> — {_esc(r.get('question', ''))}</td>"
            f"<td>—</td></tr>"
        )
    return "".join(rows)


def traces_row(data: ReportData) -> str:
    colors = {"ok": "#16a34a", "partial": "#d97706", "violated": "#dc2626"}
    out = []
    for tr in data.traces:
        color = colors.get(tr.get("status", "partial"), "#6b7280")
        steps = ""
        for s in tr.get("steps", []):
            ev_ids = "".join(
                f"<span class='tag'>{_esc(e)}</span>" for e in s.get("evidence_ids", [])
            ) or "<span class='sub'>无证据</span>"
            steps += (
                f"<div class='step'><b>{_esc(s.get('step_id', ''))}</b> · {_esc(s.get('description', ''))} "
                f"<span class='badge' style='color:{color};border-color:{color}'>{_esc(s.get('status', ''))}</span>"
                f"<div class='ev'>{ev_ids}</div></div>"
            )
        out.append(
            f"<div class='trace-card'>"
            f"<div class='trace-title'>{_esc(tr.get('name', ''))} "
            f"<span class='badge' style='color:{color};border-color:{color}'>"
            f"{_esc(tr.get('status', 'partial'))}</span></div>"
            f"<div class='steps'>{steps}</div></div>"
        )
    return "".join(out)


def evidence_table(data: ReportData) -> str:
    seen = set()
    rows = []
    for fact in data.survey.get("facts", []):
        evidences = []
        if fact.get("evidence"):
            evidences.append(fact["evidence"])
        evidences.extend(fact.get("consumer_evidence", []))
        for ev in evidences:
            key = (ev.get("file"), ev.get("symbol"), ev.get("line_start"))
            if key in seen:
                continue
            seen.add(key)
            copy_payload = json.dumps({
                "file": ev.get("file", ""), "symbol": ev.get("symbol", ""),
                "lines": f"{ev.get('line_start', 0)}-{ev.get('line_end', 0)}",
                "extractor": ev.get("extractor", ""),
                "evidence_id": ev.get("evidence_id", ""),
                "file_digest": ev.get("file_digest", ""),
            })
            rows.append(
                f"<tr><td><code>{_esc(ev.get('file', ''))}</code></td>"
                f"<td><code>{_esc(ev.get('symbol', ''))}</code></td>"
                f"<td>{_esc(ev.get('line_start', 0))}–{_esc(ev.get('line_end', 0))}</td>"
                f"<td><code class='digest'>{_esc(ev.get('file_digest', ''))}</code></td>"
                f"<td><span class='tag'>{_esc(ev.get('extractor', ''))}</span> "
                f"{_esc(ev.get('epistemic_status', ''))}"
                f"<button type='button' class='copy-btn' data-copy='{_esc(copy_payload)}' "
                f"aria-label='copy evidence'>⧉</button></td></tr>"
            )
    return "".join(rows)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaperForge 架构审计报告</title>
<style>
  :root { --bg:#0f1115; --card:#171a21; --line:#2a2f3a; --text:#e5e7eb; --muted:#9ca3af; --accent:#60a5fa; }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  @media (prefers-reduced-motion: reduce) { html { scroll-behavior:auto; } * { transition:none !important; animation:none !important; } }
  .wrap { max-width:1150px; margin:0 auto; padding:32px 24px 80px; }
  h1 { font-size:26px; margin:0 0 4px; }
  h2 { font-size:19px; margin:40px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  h2 .anchor { color:var(--muted); text-decoration:none; font-size:14px; margin-left:8px; }
  h3 { font-size:15px; margin:14px 0 6px; }
  .sub { color:var(--muted); font-size:13px; }
  code { background:#1e232c; padding:1px 6px; border-radius:4px; font-size:12.5px; }
  .digest { color:var(--muted); font-size:11.5px; word-break:break-all; }
  .meta { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 4px; }
  .meta span { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:4px 10px; font-size:12.5px; color:var(--muted); }
  .banner { display:flex; align-items:center; gap:14px; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 18px; margin:18px 0; }
  .banner .big { font-size:20px; font-weight:700; }
  .filters { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
  .filters a { color:var(--muted); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:3px 12px; font-size:12.5px; }
  .filters a:hover, .filters a[aria-current="true"] { color:var(--accent); border-color:var(--accent); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
  .layer-card,.asset-card,.trace-card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
  .layer-name { font-weight:700; }
  .layer-desc { color:var(--muted); font-size:13px; margin:6px 0 8px; }
  .badge { border:1px solid var(--line); border-radius:999px; padding:1px 10px; font-size:12px; white-space:nowrap; }
  .tag { background:#1e232c; border:1px solid var(--line); border-radius:4px; padding:0 6px; font-size:11px; color:var(--muted); margin-left:4px; white-space:nowrap; }
  .asset-card .badge { font-family:ui-monospace,monospace; }
  .unit { color:var(--muted); font-size:12px; margin-top:6px; word-break:break-all; }
  table { width:100%; border-collapse:collapse; margin-top:10px; font-size:13.5px; }
  th,td { text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--muted); font-weight:600; font-size:12.5px; text-transform:uppercase; letter-spacing:.03em; }
  .ev { margin-top:6px; font-size:12px; color:var(--muted); }
  .steps { display:flex; flex-direction:column; gap:6px; margin-top:8px; }
  .step { background:#1e232c; border-left:3px solid var(--accent); padding:5px 10px; border-radius:0 6px 6px 0; font-size:13px; }
  .trace-title { font-weight:700; }
  .review-box { background:var(--card); border:1px solid #4c1d95; border-radius:10px; padding:14px 18px; margin-top:10px; }
  .review-box .rationale { color:var(--muted); font-size:13px; margin-top:8px; }
  .note { color:var(--muted); font-size:12.5px; margin-top:8px; }
  .files a { color:var(--accent); text-decoration:none; margin-right:10px; font-size:13px; }
  .copy-btn { background:transparent; border:1px solid var(--line); color:var(--muted); border-radius:4px; cursor:pointer; font-size:12px; padding:0 6px; margin-left:6px; }
  .copy-btn:hover { color:var(--accent); border-color:var(--accent); }
  footer { margin-top:48px; color:var(--muted); font-size:12px; text-align:center; }
  @media (max-width:640px) {
    .wrap { padding:20px 12px 60px; }
    h1 { font-size:22px; }
    .banner { flex-direction:column; align-items:flex-start; }
    table { font-size:12.5px; }
    th,td { padding:7px 8px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <h1>PaperForge 架构审计报告</h1>
  <div class="sub">Architecture Audit · 五层模型 + 真实证据 + 确定性诊断（#131/#133/#134）</div>
  <div class="meta">__META__</div>

  __BANNER__

  <h2 id="layers">1 · 五层不可变模型 <a class="anchor" href="#layers">#</a></h2>
  <div class="grid">__LAYERS__</div>

  <h2 id="assets">2 · 资产组与发布单元 <a class="anchor" href="#assets">#</a></h2>
  <div class="grid">__ASSETS__</div>

  <h2 id="operations">3 · 操作（contract operations × observed facts） <a class="anchor" href="#operations">#</a></h2>
  <div class="grid">__OPERATIONS__</div>

  <h2 id="signals">4 · 信号（signal pairing） <a class="anchor" href="#signals">#</a></h2>
  <table>
    <thead><tr><th>signal</th><th>producer</th><th>consumer kind</th><th>consumer</th><th>code consumer</th><th>evidence</th></tr></thead>
    <tbody>__SIGNALS__</tbody>
  </table>

  <h2 id="traces">5 · 关键操作链路（trace，每步绑定证据） <a class="anchor" href="#traces">#</a></h2>
  __TRACES__

  <h2 id="findings">6 · 确定性发现（deterministic findings） <a class="anchor" href="#findings">#</a></h2>
  <div class="filters" role="navigation" aria-label="findings filter">
    <a href="#findings" data-filter="all" aria-current="true">全部</a>
    <a href="#findings" data-filter="violated">violated</a>
    <a href="#findings" data-filter="unresolved">unresolved</a>
    <a href="#findings" data-filter="satisfied">satisfied</a>
    <a href="#findings" data-filter="planned_gap">planned gap</a>
  </div>
  <table>
    <thead><tr><th>规则</th><th>状态</th><th>严重度</th><th>诊断与证据</th></tr></thead>
    <tbody data-findings>__FINDINGS__</tbody>
  </table>

  <h2 id="coverage">7 · 覆盖情况（诚实标注） <a class="anchor" href="#coverage">#</a></h2>
  <table>
    <thead><tr><th>extractor</th><th>状态</th><th>要求</th><th>诊断</th></tr></thead>
    <tbody>__COVERAGE__</tbody>
  </table>
  <div class="note">gate_eligible=false 是刻意保守（#133 收集器落地前不假装覆盖完整），不表示问题已清空。</div>

  <h2 id="review">8 · Review 层（maintainer_annotation — 语义判断独立于确定性发现） <a class="anchor" href="#review">#</a></h2>
  <div class="review-box">
    <table>
      <thead><tr><th>id</th><th>类型</th><th>内容</th><th>认识论状态</th></tr></thead>
      <tbody>__REVIEW__</tbody>
    </table>
    <div class="rationale"><b>rationale：</b>__RATIONAL__</div>
  </div>

  <h2 id="evidence">9 · 证据索引（全部完整 digest） <a class="anchor" href="#evidence">#</a></h2>
  <table>
    <thead><tr><th>文件</th><th>符号</th><th>行</th><th>sha256</th><th>来源 / 状态</th></tr></thead>
    <tbody>__EVIDENCE__</tbody>
  </table>

  <h2 id="data">10 · 原始数据（可独立验真） <a class="anchor" href="#data">#</a></h2>
  <div class="files">
    <a href="contract.json">contract.json</a><a href="survey.json">survey.json</a>
    <a href="audit.json">audit.json</a><a href="review.json">review.json</a>
    <a href="view.json">view.json</a><a href="traces.json">traces.json</a>
    <a href="summary.json">summary.json</a>
  </div>
  <div class="note">HTML 中 digest 为完整值；所有判断可对照同目录 JSON 复算（orchestrator/render 可重跑）。</div>

  <footer>由 paperforge.architecture_audit 纯 reconciler（#131）生成 · Review 层 = maintainer_annotation（#132 语义）· 人工解释永不进入 deterministic 投影 · HTML 是可再生成的投影，非架构事实层</footer>
</div>
<script>
(() => {
  const tbody = document.querySelector('[data-findings]');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const links = document.querySelectorAll('.filters a');
  links.forEach(link => link.addEventListener('click', (e) => {
    e.preventDefault();
    const filter = link.dataset.filter;
    links.forEach(l => l.setAttribute('aria-current', l === link ? 'true' : 'false'));
    rows.forEach(row => {
      const badge = row.querySelector('.badge');
      const status = badge ? badge.textContent.trim().split(' ').pop() : '';
      row.hidden = filter !== 'all' && status !== filter;
    });
  }));
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = '⧉'; }, 1200);
      } catch (_) { /* clipboard unavailable — button remains */ }
    });
  });
})();
</script>
</body>
</html>
"""


def render(data: ReportData) -> str:
    """Render the full self-contained HTML projection (deterministic)."""
    review = data.review
    replacements = {
        "__META__": meta_row(data),
        "__BANNER__": banner(data),
        "__LAYERS__": layers_row(data),
        "__ASSETS__": assets_row(data),
        "__OPERATIONS__": operations_row(data),
        "__SIGNALS__": signals_row(data),
        "__TRACES__": traces_row(data),
        "__FINDINGS__": findings_table(data),
        "__COVERAGE__": coverage_table(data),
        "__REVIEW__": review_table(data),
        "__RATIONAL__": _esc(review.get("rationale", "")) if review else "",
        "__EVIDENCE__": evidence_table(data),
    }
    out = HTML_TEMPLATE
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperforge-architecture-render", description="Render self-contained architecture audit HTML (#134).")
    parser.add_argument("--dir", required=True, help="directory with audit.json (+ optional review/survey/contract/traces/summary)")
    parser.add_argument("--out", required=True, help="output HTML path")
    args = parser.parse_args(argv)
    data = ReportData.from_dir(Path(args.dir))
    out_path = Path(args.out)
    out_path.write_text(render(data), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
