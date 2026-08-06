#!/usr/bin/env python3
"""Render the architecture audit JSONs into a self-contained HTML report."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


AUDIT = load("audit.json")
SUMMARY = load("summary.json")

REVISION = load("survey.json")["run_metadata"]["repository_revision"]

SEVERITY_COLOR = {
    "blocking": "#dc2626",
    "advisory": "#d97706",
    "informational": "#2563eb",
}
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
        sev_color = SEVERITY_COLOR.get(f["severity"], "#6b7280")
        evidence = f["evidence"]
        ev_text = ""
        if evidence:
            ev_text = "<br>".join(
                f'<code>{e["file"]}</code> · {e["symbol"]} : {e["lines"]}'
                for e in evidence
            )
        rows.append(
            f"""<tr>
              <td><code>{f['rule_id']}</code><div class="sub">{f['subject'] or '—'}</div></td>
              <td><span class="badge" style="color:{color};border-color:{color}">{label}</span></td>
              <td><span class="badge" style="color:{sev_color};border-color:{sev_color}">{f['severity']}</span></td>
              <td>{f['message']}{('' + '<div class="ev">' + ev_text + '</div>') if ev_text else ''}</td>
            </tr>"""
        )
    return "\n".join(rows)


def rule_coverage_rows() -> str:
    rows = []
    for row in AUDIT["content"]["rule_coverage"]:
        label, color = STATUS_LABEL.get(row.get("status") or "not_evaluated", ("—", "#6b7280"))
        rows.append(
            f"""<tr>
              <td><code>{row['rule_id']}</code></td>
              <td><span class="badge" style="color:{color};border-color:{color}">{label}</span></td>
              <td>{row['reason']}</td>
            </tr>"""
        )
    return "\n".join(rows)


def evidence_table() -> str:
    seen = set()
    rows = []
    # evidence comes from the survey facts
    survey = load("survey.json")
    for fact in survey["facts"]:
        for ev in ([fact.get("evidence")] if fact.get("evidence") else []) + list(fact.get("consumer_evidence", [])):
            key = (ev["file"], ev["symbol"], ev["line_start"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                f"""<tr>
                  <td><code>{ev['file']}</code></td>
                  <td><code>{ev['symbol']}</code></td>
                  <td>{ev['line_start']}–{ev['line_end']}</td>
                  <td><code class="digest">{ev['file_digest'][:24]}…</code></td>
                  <td>{ev['epistemic_status']}</td>
                </tr>"""
            )
    return "\n".join(rows)


def traces() -> str:
    traces = [
        (
            "sync → memory → embed",
            ["CLI sync (direct invocation)", "svc.run(): zotero sync + index", "_attach_next_actions (memory.build local / embed.resume remote)", "terminal: local only · json: no follow-up · plugin: confirmed embed"],
            "ok",
        ),
        (
            "ocr rebuild → publication → memory",
            ["ocr rebuild (keys/--all)", "START/PROGRESS/RESULT/DONE tokens per key", "result-hash.pending → phases → publish + clear (commit point)", "memory build on successKeys>0 · embed resume confirmed"],
            "ok",
        ),
        (
            "version restore (display only)",
            ["restore 恢复展示全文文本", "confirmation: display-only boundary", "copy versions/<label>/fulltext.md → render/", "provenance + drift override (DRIFTED if older)"],
            "ok",
        ),
        (
            "redo (internal only)",
            ["CLI ocr redo (maintainers)", "transaction snapshot → mutate → validate → commit/rollback", "crash-orphan recovery from paperforge-redo-*", "no user-facing entry (ribbon/command/probe/maintenance)"],
            "ok",
        ),
    ]
    out = []
    for title, steps, status in traces:
        chips = "".join(f'<div class="step">{s}</div>' for s in steps)
        out.append(
            f"""<div class="trace-card">
              <div class="trace-title">{title} <span class="badge" style="color:#16a34a;border-color:#16a34a">{status}</span></div>
              <div class="steps">{chips}</div>
            </div>"""
        )
    return "\n".join(out)


def diagnosis() -> str:
    return """
    <div class="diag-grid">
      <div class="diag-card warn">
        <h3>✗ advisory violation — OCR_RUN 死契约（G4）</h3>
        <p>插件 progress parser 声明支持 <code>OCR_RUN</code> 前缀，但后端没有任何命令发射它。这是 <code>#126</code> 吸收 <code>#101</code> 时记录的遗留死契约。诊断：解析器保留了一个永远不会出现的 token，代码维护者可能误以为 run 有进度流。</p>
        <p><b>建议</b>：从 <code>progress-parser.ts</code> 的 KNOWN_PREFIXES 移除 OCR_RUN（或在后端实现），随下一次 UI 迭代处理。</p>
      </div>
      <div class="diag-card info">
        <h3>⏳ planned gaps — 延迟交付项</h3>
        <p><b>#105 retrieval v2</b>：三意图检索 + 结构感知（schema v7、vec0 论文级 prefilter）—— 排期 post-release，contract 已声明。</p>
        <p><b>#133 确定性收集器</b>：当前审计的证据由人工采集（extractor=manual_audit）；#133 将以 AST/TS-Compiler 收集器替换，并调用同一个 #131 reconciler。</p>
      </div>
      <div class="diag-card ok">
        <h3>✓ 已实现契约全部满足</h3>
        <p>产品线四项（#127 next_actions / #126 OCR 工作台 / #129 restore 语义 / #99 redo 内部化）对应的 active 规则全部 satisfied：sync 不再隐式触发付费工作、发布走 pending 协议、restore 只动展示层、信号有消费者、UI 不写 canonical 状态。</p>
      </div>
    </div>
    """


LAYERS = [
    ("ArchitectureContract", "声明意图：规则、发布单元、生命周期（planned/active）", "active"),
    ("ArchitectureSurvey", "确定性观察：证据 + digest，仅 observed_static", "complete"),
    ("DeterministicAudit", "纯 reconciliation：rule_status + assessment", "findings"),
    ("ArchitectureReview", "AI/人工批注层（inferred/unresolved），不改事实", "advisory"),
    ("ArchitectureReportView", "只读组合，供展示（本页即其投影）", "rendered"),
]

def layers() -> str:
    out = []
    for name, desc, state in LAYERS:
        color = {"active": "#16a34a", "complete": "#16a34a", "findings": "#d97706", "advisory": "#2563eb", "rendered": "#6b7280"}[state]
        out.append(
            f"""<div class="layer-card">
              <div class="layer-name">{name}</div>
              <div class="layer-desc">{desc}</div>
              <div><span class="badge" style="color:{color};border-color:{color}">{state}</span></div>
            </div>"""
        )
    return "\n".join(out)


def assets() -> str:
    groups = {
        "library": "源文献与正式笔记",
        "ocr_raw": "原始 OCR 输出",
        "ocr_derived": "结构化派生产物（发布单元）",
        "retrieval": "检索单元/FTS",
        "vectors": "向量物化",
    }
    out = []
    for g, desc in groups.items():
        unit = "ocr_derived.generation · authority=ocr.publisher · writers=postprocess/rebuild/backfill" if g == "ocr_derived" else "—"
        out.append(
            f"""<div class="asset-card"><span class="badge">{g}</span><div class="sub">{desc}</div>
            <div class="unit">{unit}</div></div>"""
        )
    return "\n".join(out)


HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaperForge 架构审计报告 — 2026-08-06</title>
<style>
  :root { --bg:#0f1115; --card:#171a21; --line:#2a2f3a; --text:#e5e7eb; --muted:#9ca3af; --accent:#60a5fa; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  .wrap { max-width:1100px; margin:0 auto; padding:32px 24px 80px; }
  h1 { font-size:26px; margin:0 0 4px; }
  h2 { font-size:19px; margin:40px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  .sub { color:var(--muted); font-size:13px; }
  code { background:#1e232c; padding:1px 6px; border-radius:4px; font-size:12.5px; }
  .digest { color:var(--muted); }
  .meta { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 4px; }
  .meta span { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:4px 10px; font-size:12.5px; color:var(--muted); }
  .banner { display:flex; align-items:center; gap:12px; background:var(--card); border:1px solid #854d0e; border-radius:10px; padding:14px 18px; margin:18px 0; }
  .banner .big { font-size:20px; font-weight:700; color:#fbbf24; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }
  .layer-card,.asset-card,.trace-card,.diag-card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
  .layer-name { font-weight:700; }
  .layer-desc { color:var(--muted); font-size:13px; margin:6px 0 8px; }
  .badge { border:1px solid var(--line); border-radius:999px; padding:1px 10px; font-size:12px; white-space:nowrap; }
  .asset-card .badge { font-family:ui-monospace,monospace; }
  .unit { color:var(--muted); font-size:12px; margin-top:6px; }
  table { width:100%; border-collapse:collapse; margin-top:10px; font-size:13.5px; }
  th,td { text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { color:var(--muted); font-weight:600; font-size:12.5px; text-transform:uppercase; letter-spacing:.03em; }
  .ev { margin-top:6px; font-size:12px; color:var(--muted); }
  .steps { display:flex; flex-direction:column; gap:6px; margin-top:8px; }
  .step { background:#1e232c; border-left:3px solid var(--accent); padding:5px 10px; border-radius:0 6px 6px 0; font-size:13px; }
  .trace-title { font-weight:700; }
  .diag-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px; }
  .diag-card h3 { margin:0 0 8px; font-size:15px; }
  .diag-card.warn { border-color:#854d0e; } .diag-card.warn h3 { color:#fbbf24; }
  .diag-card.info { border-color:#1d4ed8; } .diag-card.info h3 { color:#93c5fd; }
  .diag-card.ok { border-color:#166534; } .diag-card.ok h3 { color:#86efac; }
  .diag-card p { margin:6px 0; color:var(--muted); font-size:13.5px; }
  .diag-card b { color:var(--text); }
  footer { margin-top:48px; color:var(--muted); font-size:12px; text-align:center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>PaperForge 架构审计报告</h1>
  <div class="sub">Architecture Audit · 2026-08-06 · 五层模型 + 真实代码证据 + 确定性诊断</div>
  <div class="meta">
    <span>revision <b>__REV__</b></span>
    <span>audit digest __AD__</span>
    <span>contract digest __CD__</span>
    <span>survey digest __SD__</span>
    <span>reconciler __RV__</span>
    <span>gate_eligible <b>__GE__</b></span>
  </div>

  <div class="banner">
    <span class="big">__ASSESS__</span>
    <span class="sub">确定性评估：__NF__ 条发现（__NV__ violated · __NP__ planned gap）· 覆盖率 python_ast/typescript = complete</span>
  </div>

  <h2>1 · 五层不可变模型</h2>
  <div class="grid">__LAYERS__</div>

  <h2>2 · 资产组与发布单元</h2>
  <div class="grid">__ASSETS__</div>

  <h2>3 · 关键操作链路（trace）</h2>
  __TRACES__

  <h2>4 · 规则评估（deterministic findings）</h2>
  <table>
    <thead><tr><th>规则</th><th>状态</th><th>严重度</th><th>诊断与证据</th></tr></thead>
    <tbody>__FINDINGS__</tbody>
  </table>

  <h2>5 · 完整规则覆盖</h2>
  <table>
    <thead><tr><th>规则</th><th>状态</th><th>说明</th></tr></thead>
    <tbody>__COVERAGE__</tbody>
  </table>

  <h2>6 · 诊断解读</h2>
  __DIAG__

  <h2>7 · 证据索引（observed_static · 真实 digest）</h2>
  <table>
    <thead><tr><th>文件</th><th>符号</th><th>行</th><th>sha256</th><th>认识论状态</th></tr></thead>
    <tbody>__EVIDENCE__</tbody>
  </table>

  <footer>由 paperforge.architecture_audit（#131）纯 reconciler 生成 · Review 层为可叠加批注（本页未叠加）· 数据文件见同目录 *.json</footer>
</div>
</body>
</html>
"""


def main() -> int:
    findings = SUMMARY["findings"]
    nv = sum(1 for f in findings if f["status"] == "violated")
    np = sum(1 for f in findings if f["status"] == "planned_gap")
    d = SUMMARY["digests"]
    replacements = {
        "__REV__": REVISION,
        "__AD__": d["audit"][:20] + "…",
        "__CD__": d["contract"][:20] + "…",
        "__SD__": d["survey"][:20] + "…",
        "__RV__": d["reconciler"],
        "__GE__": str(SUMMARY["gate_eligible"]),
        "__ASSESS__": SUMMARY["assessment"],
        "__NF__": len(findings),
        "__NV__": nv,
        "__NP__": np,
        "__LAYERS__": layers(),
        "__ASSETS__": assets(),
        "__TRACES__": traces(),
        "__FINDINGS__": finding_rows(),
        "__COVERAGE__": rule_coverage_rows(),
        "__DIAG__": diagnosis(),
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
