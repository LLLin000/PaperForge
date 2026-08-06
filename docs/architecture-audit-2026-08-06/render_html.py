#!/usr/bin/env python3
"""Render the architecture audit JSONs into a self-contained HTML report (v2).

v2 fixes: real revision + dirty state, honest coverage (unavailable collectors),
full digests (untruncated), Review overlay section (maintainer annotations are
kept out of the deterministic view), trace steps bound to evidence ids, and a
link block to the raw JSON data files.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


SUMMARY = load("summary.json")
AUDIT = load("audit.json")
REVIEW = load("review.json")
TRACES = load("traces.json")

SEVERITY_COLOR = {"blocking": "#dc2626", "advisory": "#d97706", "informational": "#2563eb"}
STATUS_LABEL = {
    "satisfied": ("✓ satisfied", "#16a34a"),
    "violated": ("✗ violated", "#dc2626"),
    "planned_gap": ("⏳ planned gap", "#2563eb"),
    "exception_applied": ("ⓘ exception", "#7c3aed"),
    "unresolved": ("? unresolved", "#d97706"),
    "not_evaluated": ("— not evaluated", "#6b7280"),
}


def finding_rows() -> str:
    rows = []
    for f in SUMMARY["findings"]:
        label, color = STATUS_LABEL.get(f["status"], (f["status"], "#6b7280"))
        sev = SEVERITY_COLOR.get(f["severity"], "#6b7280")
        ev = f["evidence"]
        ev_text = ""
        if ev:
            ev_text = "<br>".join(
                f'<code>{e["file"]}</code> · {e["symbol"]} : {e["lines"]}'
                f'<span class="tag">{e["extractor"]}</span>'
                for e in ev
            )
        rows.append(
            f"<tr><td><code>{f['rule_id']}</code><div class='sub'>{f['subject'] or '—'}</div></td>"
            f"<td><span class='badge' style='color:{color};border-color:{color}'>{label}</span></td>"
            f"<td><span class='badge' style='color:{sev};border-color:{sev}'>{f['severity']}</span></td>"
            f"<td>{f['message']}{('<div class=ev>' + ev_text + '</div>') if ev_text else ''}</td></tr>"
        )
    return "\n".join(rows)


def review_rows() -> str:
    rows = []
    for a in REVIEW.get("adjudications", []):
        rows.append(
            f"<tr><td><code>{a['finding_id']}</code></td>"
            f"<td><span class='badge' style='color:#7c3aed;border-color:#7c3aed'>{a['adjudication']}</span></td>"
            f"<td>{a['rationale']}</td>"
            f"<td><span class='badge'>{a['epistemic_status']}</span></td></tr>"
        )
    for s in REVIEW.get("semantic_findings", []):
        rows.append(
            f"<tr><td><code>{s['finding_id']}</code></td>"
            f"<td><span class='badge' style='color:#7c3aed;border-color:#7c3aed'>semantic finding</span></td>"
            f"<td>{s['message']}</td>"
            f"<td><span class='badge'>{s['epistemic_status']}</span></td></tr>"
        )
    for r in REVIEW.get("evidence_requests", []):
        rows.append(
            f"<tr><td><code>{r['request_id']}</code></td>"
            f"<td><span class='badge' style='color:#d97706;border-color:#d97706'>evidence request</span></td>"
            f"<td><b>{r['subject']}</b> — {r['question']}</td><td>—</td></tr>"
        )
    return "\n".join(rows)


def coverage_rows() -> str:
    rows = []
    for c in AUDIT["content"]["coverage"]:
        state = c["status"]
        color = {"complete": "#16a34a", "unavailable": "#d97706", "partial": "#d97706", "failed": "#dc2626"}.get(state, "#6b7280")
        rows.append(
            f"<tr><td><code>{c['extractor']}</code></td>"
            f"<td><span class='badge' style='color:{color};border-color:{color}'>{state}</span></td>"
            f"<td>{'required' if c.get('required') else 'optional'}</td>"
            f"<td>{'；'.join(c.get('diagnostics', []))}</td></tr>"
        )
    return "\n".join(rows)


def evidence_table() -> str:
    seen = set()
    rows = []
    survey = load("survey.json")
    for fact in survey["facts"]:
        for ev in ([fact.get("evidence")] if fact.get("evidence") else []) + list(fact.get("consumer_evidence", [])):
            key = (ev["file"], ev["symbol"], ev["line_start"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                f"<tr><td><code>{ev['file']}</code></td><td><code>{ev['symbol']}</code></td>"
                f"<td>{ev['line_start']}–{ev['line_end']}</td>"
                f"<td><code class='digest'>{ev['file_digest']}</code></td>"
                f"<td><span class='tag'>{ev['extractor']}</span> {ev['epistemic_status']}</td></tr>"
            )
    return "\n".join(rows)


def traces() -> str:
    out = []
    for tr in TRACES:
        steps = "".join(f"<div class='step'>{s}</div>" for s in tr["steps"])
        ev_ids = "".join(
            f"<span class='tag'>{e}</span>" for e in tr["evidence"] if e
        ) or "<span class='sub'>no evidence bound</span>"
        out.append(
            f"<div class='trace-card'><div class='trace-title'>{tr['name']} "
            f"<span class='badge' style='color:#16a34a;border-color:#16a34a'>{tr['status']}</span></div>"
            f"<div class='steps'>{steps}</div>"
            f"<div class='ev'>evidence: {ev_ids}</div></div>"
        )
    return "\n".join(out)


def layers() -> str:
    data = [
        ("ArchitectureContract", "声明意图：规则、发布单元、生命周期", "11 rules"),
        ("ArchitectureSurvey", "确定性观察：证据 + digest（人工/测试支撑）", "extractors 1/3"),
        ("DeterministicAudit", "纯 reconciliation：rule_status + assessment", SUMMARY["assessment"]),
        ("ArchitectureReview", "维护者注解层（inferred/unresolved）", REVIEW.get("reviewer_type", "—")),
        ("ArchitectureReportView", "只读组合投影（本页）", "review bound ✓"),
    ]
    out = []
    for name, desc, state in data:
        out.append(
            f"<div class='layer-card'><div class='layer-name'>{name}</div>"
            f"<div class='layer-desc'>{desc}</div><div><span class='badge'>{state}</span></div></div>"
        )
    return "\n".join(out)


def assets() -> str:
    contract = load("contract.json")
    groups = {
        "library": "源文献与正式笔记",
        "ocr_raw": "原始 OCR 输出",
        "ocr_derived": "结构化派生产物",
        "retrieval": "检索单元/FTS",
        "vectors": "向量物化",
    }
    out = []
    for g, desc in groups.items():
        units = [u["unit_id"] for u in contract["publication_units"] if u["asset_group"] == g]
        unit_text = "；".join(units) if units else "—"
        out.append(
            f"<div class='asset-card'><span class='badge'>{g}</span><div class='sub'>{desc}</div>"
            f"<div class='unit'>units: {unit_text}</div></div>"
        )
    return "\n".join(out)


def banner() -> str:
    if SUMMARY["gate_eligible"]:
        color, label = "#fbbf24", SUMMARY["assessment"]
    else:
        color, label = "#94a3b8", SUMMARY["assessment"] + " · gate 不可用"
    reasons = " · ".join(SUMMARY["reasons"]) or "—"
    return f"""
    <div class="banner">
      <span class="big" style="color:{color}">{label}</span>
      <span class="sub">确定性评估 · {len(SUMMARY['findings'])} 条发现
      （{sum(1 for f in SUMMARY['findings'] if f['status']=='unresolved')} unresolved ·
       {sum(1 for f in SUMMARY['findings'] if f['status']=='planned_gap')} planned gap）<br>
      原因：{reasons}</span>
    </div>"""


HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaperForge 架构审计报告 — 2026-08-06</title>
<style>
  :root { --bg:#0f1115; --card:#171a21; --line:#2a2f3a; --text:#e5e7eb; --muted:#9ca3af; --accent:#60a5fa; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  .wrap { max-width:1150px; margin:0 auto; padding:32px 24px 80px; }
  h1 { font-size:26px; margin:0 0 4px; }
  h2 { font-size:19px; margin:40px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  h3 { font-size:15px; margin:14px 0 6px; }
  .sub { color:var(--muted); font-size:13px; }
  code { background:#1e232c; padding:1px 6px; border-radius:4px; font-size:12.5px; }
  .digest { color:var(--muted); font-size:11.5px; word-break:break-all; }
  .meta { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 4px; }
  .meta span { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:4px 10px; font-size:12.5px; color:var(--muted); }
  .banner { display:flex; align-items:center; gap:14px; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 18px; margin:18px 0; }
  .banner .big { font-size:20px; font-weight:700; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; }
  .layer-card,.asset-card,.trace-card,.diag-card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
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
  footer { margin-top:48px; color:var(--muted); font-size:12px; text-align:center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>PaperForge 架构审计报告</h1>
  <div class="sub">Architecture Audit · 2026-08-06 · 五层模型 + 真实证据 + 确定性诊断（v2：诚实覆盖）</div>
  <div class="meta">
    <span>revision <b>__REV__</b></span>
    <span>dirty <b>__DIRTY__</b></span>
    <span>audit <span class="digest">__AD__</span></span>
    <span>contract <span class="digest">__CD__</span></span>
    <span>survey <span class="digest">__SD__</span></span>
    <span>review <span class="digest">__RD__</span></span>
    <span>reconciler __RV__</span>
  </div>

  __BANNER__

  <h2>1 · 五层不可变模型</h2>
  <div class="grid">__LAYERS__</div>

  <h2>2 · 资产组与发布单元（9 个 publication units）</h2>
  <div class="grid">__ASSETS__</div>

  <h2>3 · 关键操作链路（trace，每步绑定证据）</h2>
  __TRACES__

  <h2>4 · 确定性发现（deterministic findings）</h2>
  <table>
    <thead><tr><th>规则</th><th>状态</th><th>严重度</th><th>诊断与证据</th></tr></thead>
    <tbody>__FINDINGS__</tbody>
  </table>

  <h2>5 · 覆盖情况（诚实标注）</h2>
  <table>
    <thead><tr><th>extractor</th><th>状态</th><th>要求</th><th>诊断</th></tr></thead>
    <tbody>__COVERAGE__</tbody>
  </table>
  <div class="note">python_ast / typescript_compiler 收集器尚未实现（#133）；gate_eligible=false 是刻意保守，不表示问题已清空。</div>

  <h2>6 · Review 层（maintainer_annotation — 语义判断独立于确定性发现）</h2>
  <div class="review-box">
    <table>
      <thead><tr><th>id</th><th>类型</th><th>内容</th><th>认识论状态</th></tr></thead>
      <tbody>__REVIEW__</tbody>
    </table>
    <div class="rationale"><b>rationale：</b>__RATIONAL__</div>
  </div>

  <h2>7 · 证据索引（全部完整 digest）</h2>
  <table>
    <thead><tr><th>文件</th><th>符号</th><th>行</th><th>sha256</th><th>来源 / 状态</th></tr></thead>
    <tbody>__EVIDENCE__</tbody>
  </table>

  <h2>8 · 原始数据（可独立验真）</h2>
  <div class="files">
    <a href="contract.json">contract.json</a><a href="survey.json">survey.json</a>
    <a href="audit.json">audit.json</a><a href="review.json">review.json</a>
    <a href="view.json">view.json</a><a href="traces.json">traces.json</a>
    <a href="summary.json">summary.json</a>
  </div>
  <div class="note">HTML 中 digest 为完整值；所有判断可对照同目录 JSON 复算（build_audit.py 可重跑）。</div>

  <footer>由 paperforge.architecture_audit（#131）纯 reconciler 生成 · Review 层 = maintainer_annotation（#132 语义）· 人工解释永不进入 deterministic 投影</footer>
</div>
</body>
</html>
"""


def main() -> int:
    d = SUMMARY["digests"]
    replacements = {
        "__REV__": SUMMARY["revision"],
        "__DIRTY__": "true" if SUMMARY["dirty"] else "false",
        "__AD__": d["audit"], "__CD__": d["contract"], "__SD__": d["survey"], "__RD__": d["review"] or "—",
        "__RV__": d["reconciler"],
        "__BANNER__": banner(),
        "__LAYERS__": layers(),
        "__ASSETS__": assets(),
        "__TRACES__": traces(),
        "__FINDINGS__": finding_rows(),
        "__COVERAGE__": coverage_rows(),
        "__REVIEW__": review_rows(),
        "__RATIONAL__": REVIEW.get("rationale", ""),
        "__EVIDENCE__": evidence_table(),
    }
    html = HTML
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    out = HERE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
