import { App, Component, Modal, TFile, WorkspaceLeaf, setIcon } from "obsidian";
import { t, setLanguage } from "../../paperforge/plugin/src/i18n";
import {
  DEFAULT_SETTINGS,
  type PaperForgeSettings,
  type ProbeEnvelope,
} from "../../paperforge/plugin/src/constants";
import type {
  BaseTableSnapshotDto,
  PaperMemoryCardDto,
  PaperPdfContextDto,
  PdfAnnotationDto,
} from "../../paperforge/plugin/src/client/paperforge-client";
import { PaperForgeBasesView } from "../../paperforge/plugin/src/views/paperforge-base-view";
import { PaperForgeStatusView } from "../../paperforge/plugin/src/views/dashboard";
import { PaperForgePdfView } from "../../paperforge/plugin/src/views/pdf-annotator";
import { PaperForgeSettingTab } from "../../paperforge/plugin/src/settings";
import {
  OcrWorkspaceView,
  VersionRestoreModal,
} from "../../paperforge/plugin/src/views/ocr-workspace";
import { PaperForgeOrphanModal } from "../../paperforge/plugin/src/views/modals";
import { renderErrorAnatomy } from "../../paperforge/plugin/src/primitives";

const VAULT_ROOT = "D:/ResearchVault";
const ZOTERO_DIR = "C:/Users/Researcher/Zotero";

const OVERVIEW_MD = `# PEMF 75 Hz Osteogenic Validation

## 🔍 精读

**一句话总览:** 本文在兔 3D 琼脂糖软骨/成骨共培养模型中验证 75 Hz 脉冲电磁场通过激活 L 型钙通道（Ca2+ 内流峰值出现在 22 min）促进早期成骨分化，且该效应可被硝苯地平（10 µM）完全阻断。

### Pass 1: 概览
- 模型：48 只新西兰大白兔，12 周随访
`;

const DISCUSSION_MD = `# PEMF 75 Hz Discussions

## 会话 2026-11-18 14:20

**问题:** 为什么本文 75 Hz 的阈值效应在 150 Hz 时反而回落，硝苯地平组是否有细胞毒性对照？

**解答:** 原文在 Discussion §4.2 提出高频（150 Hz）诱导钙通道失活期延长，导致累计 Ca2+ 积分下降 [p.4, Sec. 3.2]；但正文**未报告硝苯地平单药在无 PEMF 条件下的 MTT/CCK-8 活性对照**，因此无法完全排除通道阻滞剂自身的基线抑制作用（已写入「硬伤、边界与存疑」记忆分面）。
`;

function makeMockFiles(): Record<string, string> {
  return {
    "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis/KEY_DONE.md":
      OVERVIEW_MD,
    "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis/ai/discussion.md":
      DISCUSSION_MD,
    "Resources/Literature/骨科/KEY_PENDING - Chondrocyte Scaffold/KEY_PENDING.md":
      "---\nzotero_key: KEY_PENDING\n---\n# Pending Paper\n",
    "Resources/Literature/Base/Literature Hub.base": "views:\n  - type: paperforge-table\n",
  };
}

function makeSnapshot(runningKey = "KEY_PROC"): BaseTableSnapshotDto {
  return {
    seq: 42,
    updated_at: "2026-11-18T11:20:00Z",
    rows: {
      KEY_DONE: {
        zotero_key: "KEY_DONE",
        title: "75 Hz PEMF Enhances Osteogenic Differentiation via L-Type Ca2+ Channels",
        first_author: "Zhang W.",
        year: "2025",
        journal: "Biomaterials",
        impact_factor: "12.8",
        domain: "骨科",
        has_pdf: true,
        do_ocr: false,
        analyze: true,
        ocr_status: "done",
        deep_reading_status: "done",
        main_note_path:
          "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis/KEY_DONE.md",
        user_ann_count: 4,
        agent_ann_count: 11,
        memory_facet_count: 5,
        memory_updated_at: "2026-11-18T11:15:00Z",
        needs_diagnostic: false,
      },
      KEY_PROC: {
        zotero_key: "KEY_PROC",
        title: "Dynamic Hydrogel Stiffness Regulates Chondrocyte Mechanotransduction",
        first_author: "Wang L.",
        year: "2024",
        journal: "Nat. Commun.",
        impact_factor: "14.7",
        domain: "骨科",
        has_pdf: true,
        do_ocr: true,
        analyze: true,
        ocr_status: runningKey === "KEY_PROC" ? "processing" : "pending",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/骨科/KEY_PROC - Hydrogel Mechanotransduction/KEY_PROC.md",
        user_ann_count: 0,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: false,
      },
      KEY_PENDING: {
        zotero_key: "KEY_PENDING",
        title: "Subchondral Bone Remodeling Under Cyclic Compressive Loading",
        first_author: "Li H.",
        year: "2023",
        journal: "Acta Biomater.",
        impact_factor: "9.4",
        domain: "骨科",
        has_pdf: true,
        do_ocr: true,
        analyze: false,
        ocr_status: "pending",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/骨科/KEY_PENDING - Chondrocyte Scaffold/KEY_PENDING.md",
        user_ann_count: 1,
        agent_ann_count: 0,
        memory_facet_count: 1,
        memory_updated_at: "2026-11-18T09:00:00Z",
        needs_diagnostic: false,
      },
      KEY_DEEP_WAIT: {
        zotero_key: "KEY_DEEP_WAIT",
        title: "PIEZO1 Mechanosensor Mediates Synovial Macrophage Polarization",
        first_author: "Chen R.",
        year: "2025",
        journal: "Ann. Rheum. Dis.",
        impact_factor: "20.3",
        domain: "骨科",
        has_pdf: true,
        do_ocr: false,
        analyze: true,
        ocr_status: "done",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/骨科/KEY_DEEP_WAIT - PIEZO1 Synovial/KEY_DEEP_WAIT.md",
        user_ann_count: 2,
        agent_ann_count: 6,
        memory_facet_count: 2,
        memory_updated_at: "2026-11-18T10:12:00Z",
        needs_diagnostic: false,
      },
      KEY_FAILED: {
        zotero_key: "KEY_FAILED",
        title: "Rotator Cuff Tendon-to-Bone Healing in Aged Rabbit Model (Scanned 2012)",
        first_author: "Zhou Y.",
        year: "2012",
        journal: "AJSM",
        impact_factor: "4.8",
        domain: "运动医学",
        has_pdf: true,
        do_ocr: true,
        analyze: false,
        ocr_status: "failed",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/运动医学/KEY_FAILED - Rotator Cuff/KEY_FAILED.md",
        user_ann_count: 0,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: true,
      },
      KEY_INCOMPLETE: {
        zotero_key: "KEY_INCOMPLETE",
        title: "Biphasic Calcium Phosphate Scaffold Vascularization Kinetics",
        first_author: "Liu K.",
        year: "2021",
        journal: "Bone Res.",
        impact_factor: "14.3",
        domain: "骨科",
        has_pdf: true,
        do_ocr: false,
        analyze: false,
        ocr_status: "done_incomplete",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/骨科/KEY_INCOMPLETE - BCP Scaffold/KEY_INCOMPLETE.md",
        user_ann_count: 0,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: true,
      },
      KEY_NOPDF: {
        zotero_key: "KEY_NOPDF",
        title: "Conference Abstract: Low-Intensity Pulsed Ultrasound Dose Meta-Analysis",
        first_author: "Sun Q.",
        year: "2022",
        journal: "CORR",
        impact_factor: "4.2",
        domain: "运动医学",
        has_pdf: false,
        do_ocr: false,
        analyze: false,
        ocr_status: "nopdf",
        deep_reading_status: "pending",
        main_note_path:
          "Resources/Literature/运动医学/KEY_NOPDF - Abstract/KEY_NOPDF.md",
        user_ann_count: 0,
        agent_ann_count: 0,
        memory_facet_count: 0,
        memory_updated_at: "",
        needs_diagnostic: false,
      },
    },
  };
}

function makeMemoryCard(populated = true): PaperMemoryCardDto {
  if (!populated) {
    return { paper_id: "KEY_PENDING", updated_at: "", facet_count: 0, facets: [] };
  }
  return {
    paper_id: "KEY_DONE",
    updated_at: "2026-11-18T11:15:00Z",
    facet_count: 5,
    facets: [
      {
        facet: "idea_logic",
        label: "研究思路与逻辑链",
        revision: 3,
        updated_at: "2026-11-18T11:15:00Z",
        content:
          "主线论证“物理场频率窗 → Ca2+ 内流 → ERK1/2-RUNX2 成骨分化” [Sec. 3.1-3.2]；在 15/75/150 Hz 梯度中锁定 75 Hz ± 5 µM 为有效窗口，并通过硝苯地平与 BAPTA-AM 双向阻断验证上游必要性。",
      },
      {
        facet: "methods_params",
        label: "实验技术与关键参数",
        revision: 2,
        updated_at: "2026-11-18T10:50:00Z",
        content:
          "2% 低熔点琼脂糖 3D 支架接种原代细胞；PEMF 75 Hz, 1.8 mT, 2 h/day 连续 14 天；钙成像采样率 2 Hz（峰值出现在 22 min）；抑制剂 Nifedipine 10 µM（提前 30 min 预处理）[Sec. 2.4]。",
      },
      {
        facet: "research_craft",
        label: "研究技巧与巧思",
        revision: 1,
        updated_at: "2026-11-18T09:30:00Z",
        content:
          "采用“场强等能量积分 + 变频率”对照替代固定占空比，排除热效应混杂；线性质混杂模型在附录纳入支架刚度随机截距（ICC=0.04）[Fig. 1, Sec. 4]。",
      },
      {
        facet: "critique_limits",
        label: "硬伤、边界与存疑",
        revision: 2,
        updated_at: "2026-11-18T11:15:00Z",
        content:
          "1) 正文缺少“无 PEMF + 单用 10 µM 硝苯地平”细胞活力阴性对照，无法完全切割基础增殖抑制效应；2) 48 只兔分 4 组后单组 n=12 在 12 周处死拆成 2 个时间点，每亚组仅 n=6 统计检验效能偏紧。",
      },
      {
        facet: "my_connection",
        label: "课题迁移与灵感",
        revision: 2,
        updated_at: "2026-11-18T11:10:00Z",
        content:
          "可直接复用本文 22 min 钙瞬变采集时间窗改造我们现有的 75 Hz GelMA 支架实验；但我们的对照组必须补齐 Nifedipine 单独孵育的 CCK-8 活性校验。",
      },
    ],
  };
}

function makeAnnotations(): PdfAnnotationDto[] {
  return [
    {
      ann_id: "ann_ai_skel",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "highlight",
      color: "purple",
      intent: "general",
      author: "agent",
      lens: "skeleton",
      grounding_tier: "exact_sentence",
      exact_text: "Intracellular Ca2+ transients peaked at 22 min and were abolished by nifedipine (10 µM)",
      comment:
        "【逻辑转折 · Stage 2a】通过 L 型钙通道阻断确立“Ca2+ 内流 → RUNX2 入核”因果链。",
      tags: [],
      rects: [[0.072, 0.415, 0.48, 0.482]],
      section_path: "Results > 3.1 Mechanistic Validation",
      block_id: "blk_02",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "deadbeef",
      created_at: "2026-11-18T11:02:00Z",
      updated_at: "2026-11-18T11:02:00Z",
      provenance_status: "verified",
    },
    {
      ann_id: "ann_ai_margin",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "margin",
      color: "purple",
      intent: "general",
      author: "agent",
      lens: "critique",
      grounding_tier: "margin_fallback",
      exact_text:
        "Cross-cohort linear mixed model evaluated age, sex, and scaffold stiffness covariates across 48 rabbits",
      comment:
        "【审稿警惕 · Stage 3 页边定位】4 组×2 时间点拆分后每亚组仅 n=6，检验效力偏紧。",
      tags: [],
      rects: [[0.014, 0.618, 0.025, 0.785]],
      section_path: "4. Statistical Modeling",
      block_id: "blk_03",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "deadbeef",
      created_at: "2026-11-18T11:04:00Z",
      updated_at: "2026-11-18T11:04:00Z",
      provenance_status: "verified",
    },
    {
      ann_id: "ann_u_hl",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "highlight",
      color: "yellow",
      intent: "general",
      author: "user",
      exact_text: "PEMF stimulation at 75 Hz ± 5 µM markedly enhanced galvanotaxis",
      comment: "核对我们实验室信号发生器能否稳定输出 75 Hz 矩形波。",
      tags: [],
      rects: [
        [0.072, 0.302, 0.48, 0.336],
        [0.072, 0.338, 0.44, 0.368],
      ],
      section_path: "Results > 3.1 Parameters",
      block_id: "blk_01",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "deadbeef",
      created_at: "2026-11-18T09:10:00Z",
      updated_at: "2026-11-18T09:10:00Z",
      provenance_status: "verified",
    },
    {
      ann_id: "ann_u_area",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "area",
      color: "blue",
      intent: "general",
      author: "user",
      exact_text: "",
      comment: "Fig 1 柱状图展示 75 Hz 峰值显著高于 15 Hz 与 Nifedipine 阻断组。",
      tags: [],
      rects: [[0.515, 0.28, 0.94, 0.675]],
      section_path: "Results > Fig. 1",
      block_id: "blk_fig1",
      figure_id: "figure_001",
      crop_asset_rel: "Resources/Literature/骨科/KEY_DONE/assets/KEY_DONE_ann_u_area.jpg",
      embed_wikilink: "![[KEY_DONE_ann_u_area.jpg]]",
      pdf_sha256: "deadbeef",
      created_at: "2026-11-18T09:15:00Z",
      updated_at: "2026-11-18T09:15:00Z",
      provenance_status: "verified",
    },
  ];
}

function makeEnvelopes(opts?: {
  allReady?: boolean;
  ocrRunning?: boolean;
  memoryStale?: boolean;
}): Record<string, ProbeEnvelope> {
  const now = "2026-11-18T11:20:00Z";
  return {
    installation: {
      schema_version: 2,
      module: "installation",
      capability_state: "ready",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "ok",
      reason: { code: "installation.ready", text: "托管 Python 运行时 v2.2.0 就绪。" },
      action: { primary: null },
      notices: [],
      user_state: "ready",
      capability_kind: "required",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: now,
      ttl_seconds: 300,
      details: { python_version: "3.12.8", skill_version: "2026-07-27.1" },
    },
    library: {
      schema_version: 2,
      module: "library",
      capability_state: opts?.allReady ? "ready" : "missing_input",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: opts?.allReady ? "ok" : "warning",
      reason: {
        code: opts?.allReady ? "library.ready" : "library.config_missing",
        text: opts?.allReady
          ? "已连接 Better BibTeX 导出并同步 248 篇文献。"
          : "请先指定 Zotero 数据目录并完成首次同步。",
      },
      action: opts?.allReady
        ? { primary: null }
        : {
            primary: {
              action_id: "library.sync",
              verb: "run",
              label: "立即同步",
              availability: "available",
              safety_class: "safe",
              preservation_facts: [],
              replacement_facts: [],
              interruptible: true,
              confirmation_required: false,
              confirmation_prompt: null,
              scope: "library",
              scope_count: 1,
            },
          },
      notices: [],
      user_state: opts?.allReady ? "ready" : "setup_required",
      capability_kind: "required",
      maintenance_eligible: !opts?.allReady,
      user_visible_failure: false,
      user_impact: null,
      updated_at: now,
      ttl_seconds: 300,
    },
    ocr: {
      schema_version: 2,
      module: "ocr",
      capability_state: opts?.allReady ? "ready" : "needs_action",
      activity_state: opts?.ocrRunning ? "running" : "idle",
      activity_label: opts?.ocrRunning ? "正在 OCR KEY_PROC (2/5)" : null,
      activity_progress: opts?.ocrRunning ? { current: 2, total: 5 } : null,
      severity: opts?.allReady ? "ok" : "warning",
      reason: {
        code: opts?.allReady ? "ocr.pending" : "ocr.partial_failed",
        text: opts?.allReady
          ? "有 1 篇待处理文献，可点击开始 OCR。"
          : "1 篇历史扫描件 OCR 解析失败（KEY_FAILED），建议在高级工作台诊断重建。",
      },
      action: {
        primary: {
          action_id: "ocr.run",
          verb: "run",
          label: "运行 OCR",
          availability: "available",
          safety_class: "safe",
          preservation_facts: [],
          replacement_facts: [],
          interruptible: true,
          confirmation_required: true,
          confirmation_prompt: "Run OCR?",
          scope: "ocr",
          scope_count: 2,
        },
      },
      notices: [],
      user_state: opts?.allReady ? "checking" : "action_required",
      capability_kind: "optional",
      maintenance_eligible: !opts?.allReady,
      user_visible_failure: !opts?.allReady,
      user_impact: "部分 PDF 尚未生成可检索全文与图表裁剪。",
      updated_at: now,
      ttl_seconds: 300,
      pipeline_version: "v3.2",
      last_pipeline_version: "v3.1",
      pipeline_version_summary: { stale: opts?.allReady ? 0 : 12, total: 248 },
    },
    memory: {
      schema_version: 2,
      module: "memory",
      capability_state: opts?.memoryStale ? "unknown" : "ready",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: opts?.memoryStale ? "error" : "ok",
      reason: {
        code: opts?.memoryStale ? "memory.probe_error" : "memory.ready",
        text: opts?.memoryStale
          ? "SQLite FTS5 检测响应超时，请点击诊断或重试。"
          : "FTS5 + vec0 混合检索引擎就绪（248 篇 · 6,420 个语义单元）。",
      },
      action: {
        primary: opts?.memoryStale
          ? {
              action_id: "memory.rebuild",
              verb: "rebuild",
              label: "重建记忆索引",
              availability: "available",
              safety_class: "safe",
              preservation_facts: [],
              replacement_facts: [],
              interruptible: true,
              confirmation_required: false,
              confirmation_prompt: null,
              scope: "memory",
              scope_count: 1,
            }
          : null,
      },
      notices: [],
      user_state: opts?.memoryStale ? "detection_failed" : "ready",
      capability_kind: "optional",
      maintenance_eligible: Boolean(opts?.memoryStale),
      user_visible_failure: Boolean(opts?.memoryStale),
      user_impact: opts?.memoryStale ? "全文混合检索暂不可用。" : null,
      updated_at: now,
      ttl_seconds: 300,
      details: {
        api_key_configured: true,
        build_state: { status: "idle" },
        total_papers: 248,
      },
    },
    agent: {
      schema_version: 2,
      module: "agent",
      capability_state: "unavailable",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "ok",
      reason: {
        code: "agent.not_enabled",
        text: "尚未向外部 Agent 平台部署 PaperForge Skills（可选）。",
      },
      action: { primary: null },
      notices: [],
      user_state: "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: now,
      ttl_seconds: 300,
    },
  };
}

function makeFakeSettings(overrides?: Partial<PaperForgeSettings>): PaperForgeSettings {
  return {
    ...DEFAULT_SETTINGS,
    vault_path: VAULT_ROOT,
    system_dir: ".paperforge",
    resources_dir: "Resources",
    literature_dir: "Resources/Literature",
    base_dir: "Resources/Literature/Base",
    zotero_data_dir: ZOTERO_DIR,
    agent_platform: "claude",
    language: "zh",
    _paddleocr_configured: true,
    _vector_db_configured: true,
    _setup_complete: true,
    ...overrides,
  };
}

function makeFakePlugin(app: App, snapshot: BaseTableSnapshotDto, opts?: { populatedMemory?: boolean; pdfChanged?: boolean }) {
  const anns = makeAnnotations();
  if (opts?.pdfChanged) {
    anns.forEach((a) => {
      a.provenance_status = "changed";
    });
  }
  const settings = makeFakeSettings();
  const fakeClient = {
    isOperationActive: () => true,
    cancelActiveOperation: () => {},
    backendVersion: async () => "2.2.0",
    dashboardStats: async () => ({
      items: Object.values(snapshot.rows).map((r) => ({
        ...r,
        authors: [r.first_author],
        pdf_path: r.has_pdf ? `storage:${r.zotero_key}/paper.pdf` : "",
      })),
      permissions: { can_sync: true, can_ocr: true },
    }),
    credentialAvailable: async () => true,
    getBaseTableSnapshot: async () => snapshot,
    setNoteFlag: async () => ({ ok: true }),
    getMemoryCard: async (key: string) => makeMemoryCard(opts?.populatedMemory ?? key === "KEY_DONE"),
    getPdfContext: async (key: string): Promise<PaperPdfContextDto> => ({
      paper_id: key,
      title: "75 Hz PEMF Enhances Osteogenic Differentiation via L-Type Ca2+ Channels",
      pdf_abs_path: `${ZOTERO_DIR}/storage/Z8A1/paper.pdf`,
      pdf_vault_rel: "",
      pdf_locator: "storage:Z8A1/paper.pdf",
      is_vault_relative: false,
      pdf_sha256: "e3b0c442",
      page_count: 12,
      workspace_rel: "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis",
      note_rel_path:
        "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis/KEY_DONE.md",
      annotations: anns,
    }),
    listAnnotations: async () => anns,
    adoptAnnotation: async (_k: string, id: string) => anns.find((a) => a.ann_id === id)!,
    clearAgentAnnotations: async () => ({ paper_id: "KEY_DONE", deleted_count: 2, deleted_ids: [] }),
    searchRecords: async () => [],
    probe: async (mod: string) => {
      if (mod === "lineage") {
        return {
          papers: {
            KEY_FAILED: { ocr: "failed" },
            KEY_INCOMPLETE: { ocr: "incomplete" },
          },
        };
      }
      return makeEnvelopes({ allReady: false, ocrRunning: true })[mod] ?? makeEnvelopes().ocr;
    },
    queryOcrPapers: async () => [
      {
        key: "KEY_DONE",
        title: "75 Hz PEMF Enhances Osteogenic Differentiation",
        status: "done",
        version: "v3.2",
        authors: "Zhang W.",
        year: "2025",
        pages: "12",
        can_rebuild: true,
        can_redo: true,
        recommended_action: "none",
        fulltext_path: ".paperforge/ocr/KEY_DONE/render/fulltext.md",
      },
      {
        key: "KEY_FAILED",
        title: "Rotator Cuff Tendon-to-Bone Healing in Aged Rabbit Model",
        status: "failed",
        version: "v2.8",
        authors: "Zhou Y.",
        year: "2012",
        pages: "9",
        can_rebuild: true,
        can_redo: true,
        recommended_action: "retry",
        fulltext_path: ".paperforge/ocr/KEY_FAILED/render/fulltext.md",
      },
      {
        key: "KEY_INCOMPLETE",
        title: "Biphasic Calcium Phosphate Scaffold Vascularization Kinetics",
        status: "done_incomplete",
        version: "v3.1",
        authors: "Liu K.",
        year: "2021",
        pages: "10",
        can_rebuild: true,
        can_redo: true,
        recommended_action: "rebuild",
        fulltext_path: ".paperforge/ocr/KEY_INCOMPLETE/render/fulltext.md",
      },
      {
        key: "KEY_PENDING",
        title: "Subchondral Bone Remodeling Under Cyclic Compressive Loading",
        status: "pending",
        version: "",
        authors: "Li H.",
        year: "2023",
        pages: "8",
        can_rebuild: false,
        can_redo: false,
        recommended_action: "run",
        fulltext_path: "",
      },
    ],
    readDiagnosticFulltext: async (key: string) => ({
      paper_id: key,
      content:
        "# 3.1 PEMF Stimulation Parameters (Read-Only OCR Diagnostic)\n\n" +
        "[p.1 · blk_01 · role=body_text · conf=0.98]\n" +
        "PEMF stimulation at 75 Hz ± 5 µM markedly enhanced galvanotaxis and early osteogenic differentiation...\n\n" +
        "[p.1 · fig_001 · role=figure_caption · owner=figure_001]\n" +
        "Fig 1. Osteogenic markers under 75 Hz PEMF vs sham control (*p<0.01).",
      truncated: false,
      total_lines: 6,
      total_chars: 320,
    }),
    describeAction: async (actionId: string) => ({
      action_id: actionId,
      availability: "available",
      confirmation: "not_required",
    }),
    embedStatus: async () => ({
      model: "text-embedding-3-small",
      mode: "requests",
      deps_installed: true,
      body_chunk_count: 5840,
      object_chunk_count: 580,
      total_chunks: 6420,
      build_state: { status: "idle" },
    }),
    memoryStatus: async () => ({ paper_count_db: 248, fresh: true, needs_rebuild: false }),
    versionsShow: async () => ({ versions: [], current_label: "v3.2", current_path: "" }),
    versionsBackups: async () => [],
  };

  const plugin = {
    app,
    manifest: { id: "paperforge", version: "2.2.0", name: "PaperForge" },
    settings,
    agentPlatformChoices: ["opencode", "claude", "codex", "cursor", "gemini", "windsurf"],
    _embedStatusCache: {},
    _ocrProgress: { current: 2, total: 5, key: "KEY_PROC" },
    getClient: () => fakeClient as unknown as ReturnType<never>,
    getBaseSnapshotCache: () => snapshot,
    refreshBaseSnapshot: async () => snapshot,
    isOcrRunningForKey: (key: string) => key === "KEY_PROC",
    openPaperPdf: async () => {},
    requestOcrRun: async () => {},
    triggerManualSync: () => {},
    openOcrDiagnostic: () => {},
    openModuleSettings: () => true,
    openSetupJourney: () => true,
    saveSettings: async () => {},
    _autoSync: () => {},
  };
  app.plugins.plugins["paperforge"] = plugin;
  return plugin;
}

function createScene(
  slug: string,
  title: string,
  subtitle: string,
  width = 1280
): { root: HTMLElement; body: HTMLElement } {
  (window as unknown as { __PF_STAGE__: string }).__PF_STAGE__ = slug;
  const root = document.createElement("section");
  root.id = `scene-${slug}`;
  root.className = "pf-doc-scene";
  root.style.width = `${width}px`;

  const banner = document.createElement("div");
  banner.className = "pf-doc-scene-banner";
  banner.innerHTML = `<div class="pf-doc-scene-title">${title}</div><div class="pf-doc-scene-sub">${subtitle}</div>`;
  root.appendChild(banner);

  const body = document.createElement("div");
  body.className = "pf-doc-scene-body";
  root.appendChild(body);

  document.body.appendChild(root);
  return { root, body };
}

function buildObsidianWorkspaceShell(
  parent: HTMLElement,
  opts: {
    activeTabTitle: string;
    activeRibbon: "base" | "dashboard" | "settings";
    rightSidebarTitle?: string;
    width?: string;
  }
): { mainSlot: HTMLElement; sidebarSlot?: HTMLElement } {
  const shell = parent.createDiv({ cls: "pf-ob-window" });
  if (opts.width) shell.style.width = opts.width;

  const titlebar = shell.createDiv({ cls: "pf-ob-titlebar" });
  titlebar.createDiv({
    cls: "pf-ob-titlebar-dots",
    attr: { "aria-hidden": "true" },
  }).innerHTML = '<span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>';
  titlebar.createDiv({
    cls: "pf-ob-titlebar-text",
    text: "ResearchVault - Obsidian v1.12 · PaperForge v2.2",
  });

  const workbench = shell.createDiv({ cls: "pf-ob-workbench" });

  // Left Ribbon (Option B: BookOpen Dashboard + Library Base; scan-text moved out of primary ribbon)
  const ribbon = workbench.createDiv({ cls: "pf-ob-ribbon" });
  const rIcons: Array<{ id: string; key: "dashboard" | "base" | "settings"; tip: string }> = [
    { id: "book-open", key: "dashboard", tip: "PaperForge Dashboard" },
    { id: "library", key: "base", tip: "PaperForge Literature Hub (.base)" },
    { id: "settings", key: "settings", tip: "设置 → PaperForge 控制中心" },
  ];
  for (const item of rIcons) {
    const btn = ribbon.createDiv({
      cls: `pf-ob-ribbon-icon ${opts.activeRibbon === item.key ? "is-active" : ""}`,
      title: item.tip,
    });
    setIcon(btn, item.id);
  }

  // Main workspace leaf
  const mainLeaf = workbench.createDiv({ cls: "pf-ob-main-leaf" });
  const tabHeader = mainLeaf.createDiv({ cls: "pf-ob-tab-header" });
  const tab = tabHeader.createDiv({ cls: "pf-ob-tab is-active" });
  const tabIcon = tab.createSpan({ cls: "pf-ob-tab-icon" });
  setIcon(tabIcon, opts.activeRibbon === "base" ? "table" : "file-text");
  tab.createSpan({ text: opts.activeTabTitle });

  const mainSlot = mainLeaf.createDiv({ cls: "pf-ob-leaf-content" });

  let sidebarSlot: HTMLElement | undefined;
  if (opts.rightSidebarTitle) {
    const rightDock = workbench.createDiv({ cls: "pf-ob-right-sidebar" });
    const dockHead = rightDock.createDiv({ cls: "pf-ob-tab-header" });
    const dTab = dockHead.createDiv({ cls: "pf-ob-tab is-active" });
    dTab.createSpan({ text: opts.rightSidebarTitle });
    sidebarSlot = rightDock.createDiv({ cls: "pf-ob-sidebar-content" });
  }

  return { mainSlot, sidebarSlot };
}

function buildNativeBaseChrome(
  container: HTMLElement,
  opts: {
    activeViewName: string;
    filterText: string;
    sortText: string;
    countText: string;
  }
): HTMLElement {
  const baseWrap = container.createDiv({ cls: "pf-ob-bases-container" });
  const toolbar = baseWrap.createDiv({ cls: "pf-ob-bases-toolbar" });

  const viewTabs = toolbar.createDiv({ cls: "pf-ob-bases-views" });
  for (const name of ["控制面板", "待 OCR", "待深度阅读", "高分精读集 (用户视图)"]) {
    const pill = viewTabs.createEl("span", {
      cls: `pf-ob-bases-view-pill ${name === opts.activeViewName ? "is-active" : ""}`,
      text: name,
    });
    if (name === "控制面板") pill.setAttr("data-pf-view-type", "paperforge-table");
  }

  const nativeControls = toolbar.createDiv({ cls: "pf-ob-bases-controls" });
  for (const [iconId, label] of [
    ["filter", opts.filterText],
    ["arrow-up-down", opts.sortText],
    ["sliders", "属性 (12)"],
    ["search", opts.countText],
  ]) {
    const chip = nativeControls.createEl("span", { cls: "pf-ob-bases-chip" });
    const ic = chip.createSpan({ cls: "pf-ob-chip-icon" });
    setIcon(ic, iconId);
    chip.createSpan({ text: label });
  }

  return baseWrap.createDiv({ cls: "pf-ob-bases-view-mount" });
}

function makeBaseEntries(snapshot: BaseTableSnapshotDto, keys: string[]) {
  return keys.map((k) => {
    const row = snapshot.rows[k];
    return {
      file: new TFile(row?.main_note_path || `${k}.md`),
      getValue: (propId: string) =>
        propId === "note.zotero_key" ? { data: k, toString: () => k } : null,
    };
  });
}

function populateDashboardView(
  app: App,
  container: HTMLElement,
  snapshot: BaseTableSnapshotDto,
  configure: (v: PaperForgeStatusView) => void
): PaperForgeStatusView {
  const view = new PaperForgeStatusView(new WorkspaceLeaf());
  (view as unknown as { app: App }).app = app;
  (view as unknown as { containerEl: HTMLElement }).containerEl = container;
  (view as unknown as Record<string, unknown>)._cachedStats = {
    paper_count: Object.keys(snapshot.rows).length,
  };
  (view as unknown as Record<string, unknown>)._cachedItems = Object.values(
    snapshot.rows
  ).map((r) => ({
    ...r,
    authors: [r.first_author],
    pdf_path: r.has_pdf ? `storage:${r.zotero_key}/paper.pdf` : "",
  }));
  (view as unknown as Record<string, unknown>)._dashboardPermissions = {
    can_sync: true,
    can_ocr: true,
  };
  (view as unknown as Record<string, unknown>)._paperforgeVersion = "v2.2.0";
  view._buildPanel();
  if (view._versionBadge) view._versionBadge.setText("v2.2.0");
  configure(view);
  return view;
}

export async function renderAllScenes(): Promise<void> {
  const baseApp = new App(makeMockFiles(), VAULT_ROOT);
  setLanguage(baseApp, "zh");

  // ── Scene 01: Base Workbench — All Row States + Native Base Toolbar ────────
  {
    const snap = makeSnapshot("KEY_PROC");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap, { populatedMemory: true });
    const { body } = createScene(
      "01-base-workbench-all-states",
      "01 · 原生 Obsidian Base 文献工作台（PaperForgeBasesView · type: paperforge-table）",
      "左侧边栏 library 入口 → Literature Hub.base · 物理读写分离（队列可写 + 机器状态/认知计数只读实时投影）",
      1320
    );
    const { mainSlot } = buildObsidianWorkspaceShell(body, {
      activeTabTitle: "Literature Hub.base",
      activeRibbon: "base",
    });
    const mount = buildNativeBaseChrome(mainSlot, {
      activeViewName: "控制面板",
      filterText: '筛选: file.ext == "md"',
      sortText: "排序: 年份 ↓",
      countText: "6 篇显示",
    });
    const baseView = new PaperForgeBasesView({} as never, mount, plugin as never);
    (baseView as unknown as { app: App }).app = app;
    baseView.data = {
      data: makeBaseEntries(snap, [
        "KEY_DONE",
        "KEY_PROC",
        "KEY_PENDING",
        "KEY_FAILED",
        "KEY_INCOMPLETE",
        "KEY_NOPDF",
      ]),
    } as never;
    baseView.onload();
    baseView.onDataUpdated();
  }

  // ── Scene 02: Base Filtered Preset View & Empty / Loading Boundary States ──
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap);
    const { body } = createScene(
      "02-base-empty-and-filtered-states",
      "02 · Base 预设过滤视图（「待深度阅读」）与空结果 / 加载边界态",
      "Base 原生过滤器直接决定行顺序与可见范围；PaperForgeBasesView 响应空筛选结果与初始加载",
      1320
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    // Left: Filtered view ("待深度阅读")
    const leftCard = grid.createDiv({ cls: "pf-doc-panel" });
    leftCard.createDiv({ cls: "pf-doc-panel-label", text: "A. 预设过滤视图：待深度阅读" });
    const leftMount = buildNativeBaseChrome(leftCard, {
      activeViewName: "待深度阅读",
      filterText: 'analyze == true && ocr_status == "done"',
      sortText: "排序: IF ↓",
      countText: "1 篇显示",
    });
    const bvLeft = new PaperForgeBasesView({} as never, leftMount, plugin as never);
    (bvLeft as unknown as { app: App }).app = app;
    bvLeft.data = { data: makeBaseEntries(snap, ["KEY_DEEP_WAIT"]) } as never;
    bvLeft.onload();

    // Right: Empty filtered state
    const rightCard = grid.createDiv({ cls: "pf-doc-panel" });
    rightCard.createDiv({ cls: "pf-doc-panel-label", text: "B. 筛选零命中空状态（base_empty_hint）" });
    const rightMount = buildNativeBaseChrome(rightCard, {
      activeViewName: "待 OCR",
      filterText: 'domain == "神经科" && ocr_status == "pending"',
      sortText: "排序: 默认",
      countText: "0 篇显示",
    });
    const bvRight = new PaperForgeBasesView({} as never, rightMount, plugin as never);
    (bvRight as unknown as { app: App }).app = app;
    bvRight.data = { data: [] } as never;
    bvRight.onload();
  }

  // ── Scene 03: Dashboard Global Mode (Healthy vs Unconfigured / Anomalies) ──
  {
    const { body } = createScene(
      "03-dashboard-global-modes",
      "03 · Dashboard 全局模式（Global Mode：健康运行态 vs 未配置/异常恢复态）",
      "无文献/非工作区焦点激活时的系统概览：文献统计、系统健康行、缺失环境/索引引导卡与快捷操作",
      1180
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    // Left: Healthy Global Mode
    const snapOk = makeSnapshot("");
    const appOk = new App(makeMockFiles(), VAULT_ROOT);
    const pluginOk = makeFakePlugin(appOk, snapOk);
    pluginOk.settings.capabilityState = makeEnvelopes({ allReady: true });
    const panelOk = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    panelOk.createDiv({ cls: "pf-doc-panel-label", text: "A. 正常运行态（Healthy Global）" });
    const contOk = panelOk.createDiv();
    populateDashboardView(appOk, contOk, snapOk, (v) => {
      v._currentMode = "global";
      v._renderModeHeader("global");
      v._renderGlobalMode();
      v.renderSearchSection(v._contentEl);
    });

    // Right: Backend missing & export/index anomaly state
    const emptySnap: BaseTableSnapshotDto = { seq: 0, updated_at: "", rows: {} };
    const appErr = new App({}, VAULT_ROOT);
    const pluginErr = makeFakePlugin(appErr, emptySnap);
    pluginErr.settings.capabilityState = makeEnvelopes({ allReady: false, memoryStale: true });
    (pluginErr.getClient() as unknown as Record<string, unknown>).credentialAvailable = async () => false;
    const panelErr = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    panelErr.createDiv({ cls: "pf-doc-panel-label", text: "B. 环境缺失与索引异常引导态（Recovery）" });
    const contErr = panelErr.createDiv();
    const vErr = populateDashboardView(appErr, contErr, emptySnap, (v) => {
      v._currentMode = "global";
      (v as unknown as Record<string, unknown>)._cachedItems = [];
      (v as unknown as Record<string, unknown>)._dashboardPermissions = { can_sync: false };
      v._backendUnavailable = true;
      v._renderModeHeader("global");
      (v as unknown as { _renderBackendBanner: () => void })._renderBackendBanner();
      v._renderGlobalMode();
    });
    void vErr;
  }

  // ── Scene 04: Dashboard Collection Mode ────────────────────────────────────
  {
    const snap = makeSnapshot("KEY_PROC");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(app, snap);
    const { body } = createScene(
      "04-dashboard-collection-mode",
      "04 · Dashboard 集合模式（Collection Mode · 当前激活 <domain>.base 时显示）",
      "展示单领域漏斗进度（Total → PDF Ready → OCR Done → Deep Read）、OCR 流水线分段条与领域级批量动作",
      1380
    );
    const { mainSlot, sidebarSlot } = buildObsidianWorkspaceShell(body, {
      activeTabTitle: "骨科.base",
      activeRibbon: "base",
      rightSidebarTitle: "PaperForge 伴读侧栏",
    });
    const mount = buildNativeBaseChrome(mainSlot, {
      activeViewName: "控制面板",
      filterText: 'domain == "骨科"',
      sortText: "排序: 年份 ↓",
      countText: "4 篇显示",
    });
    const bv = new PaperForgeBasesView({} as never, mount, app.plugins.plugins["paperforge"] as never);
    (bv as unknown as { app: App }).app = app;
    bv.data = {
      data: makeBaseEntries(snap, ["KEY_DONE", "KEY_PROC", "KEY_PENDING", "KEY_INCOMPLETE"]),
    } as never;
    bv.onload();

    const sSlot = sidebarSlot!.createDiv();
    populateDashboardView(app, sSlot, snap, (v) => {
      v._currentMode = "collection";
      v._currentDomain = "骨科";
      v._renderModeHeader("collection");
      v._renderCollectionMode();
    });
  }

  // ── Scene 05: Dashboard Paper Mode & 5-Facet Living Paper Memory ───────────
  {
    const snap = makeSnapshot("");
    const appDone = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(appDone, snap, { populatedMemory: true });

    const appNew = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(appNew, snap, { populatedMemory: false });

    const { body } = createScene(
      "05-dashboard-paper-mode-living-memory",
      "05 · Dashboard 单篇伴读模式 & 🧠 5 维度持续演进动态记忆卡片（Phase 3）",
      "移除旧版 9 字段人工填表按钮，转为「文章概览 + 🧠 动态认知记忆（Read-Before-Speak + Refine-Don't-Append）+ 下一步引导」",
      1260
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    // Left: Mature paper with all 5 facets + discussion + complete badge
    const left = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    left.createDiv({ cls: "pf-doc-panel-label", text: "A. 已精读论文（5 维度动态记忆已演进）" });
    const lCont = left.createDiv();
    populateDashboardView(appDone, lCont, snap, (v) => {
      const entry = {
        ...snap.rows.KEY_DONE,
        authors: ["Zhang W.", "Li M.", "Chen H."],
        pdf_path: "storage:Z8A1/paper.pdf",
        next_step: "ready",
        discussion_path:
          "Resources/Literature/骨科/KEY_DONE - 75Hz PEMF Osteogenesis/ai/discussion.md",
      };
      v._currentMode = "paper";
      v._currentPaperKey = "KEY_DONE";
      v._currentPaperEntry = entry;
      v._renderModeHeader("paper");
      v._renderPaperMode();
    });

    // Right: Newly synced paper with empty memory & pending OCR CTA
    const right = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    right.createDiv({ cls: "pf-doc-panel-label", text: "B. 待处理论文（记忆空状态 + 下一步建议）" });
    const rCont = right.createDiv();
    populateDashboardView(appNew, rCont, snap, (v) => {
      const entry = {
        ...snap.rows.KEY_PENDING,
        authors: ["Li H."],
        pdf_path: "storage:Z99/pending.pdf",
        next_step: "ocr",
        deep_reading_status: "pending",
      };
      v._currentMode = "paper";
      v._currentPaperKey = "KEY_PENDING";
      v._currentPaperEntry = entry;
      v._renderModeHeader("paper");
      v._renderPaperMode();
    });
  }

  // ── Scene 06: Dashboard Search Modes & Recovery Cards ──────────────────────
  {
    const snap = makeSnapshot("");
    const { body } = createScene(
      "06-dashboard-search-and-recovery-states",
      "06 · Dashboard 检索状态矩阵（M 元数据模式 / @ 混合深检模式 / 索引缺失恢复引导）",
      "展示 search (M)、retrieve --deep (@) 与 vectors-not-built / missing-memory-index 恢复卡",
      1280
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-3" });

    // Col 1: M Metadata search
    const app1 = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(app1, snap);
    const c1 = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    c1.createDiv({ cls: "pf-doc-panel-label", text: "A. M 元数据检索结果" });
    populateDashboardView(app1, c1.createDiv(), snap, (v) => {
      v._currentMode = "global";
      v._renderModeHeader("global");
      v.renderSearchSection(v._contentEl);
      if (v._searchInput) v._searchInput.value = "PEMF 75 Hz";
      v._searchState = "results";
      v._searchDeep = false;
      v._searchResults = [
        {
          zotero_key: "KEY_DONE",
          title: "75 Hz PEMF Enhances Osteogenic Differentiation",
          first_author: "Zhang W.",
          journal: "Biomaterials",
          year: "2025",
          score: 0.94,
          snippet: "...PEMF stimulation at 75 Hz ± 5 µM markedly enhanced...",
        },
        {
          zotero_key: "KEY_DEEP_WAIT",
          title: "PIEZO1 Mechanosensor Mediates Synovial Macrophage",
          first_author: "Chen R.",
          journal: "Ann. Rheum. Dis.",
          year: "2025",
          score: 0.81,
          snippet: "...cyclic mechanical loading and electromagnetic coupling...",
        },
      ];
      v._renderSearchState();
    });

    // Col 2: @ Deep hybrid retrieve
    const app2 = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(app2, snap);
    const c2 = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    c2.createDiv({ cls: "pf-doc-panel-label", text: "B. @ 混合深检（BM25 + 向量）" });
    populateDashboardView(app2, c2.createDiv(), snap, (v) => {
      v._currentMode = "global";
      v._renderModeHeader("global");
      v.renderSearchSection(v._contentEl);
      if (v._searchInput) v._searchInput.value = "@nifedipine Ca2+ 22 min";
      v._searchState = "results";
      v._searchDeep = true;
      v._searchResults = [
        {
          zotero_key: "KEY_DONE",
          title: "75 Hz PEMF Enhances Osteogenic Differentiation",
          first_author: "Zhang W.",
          journal: "Biomaterials",
          heading: "Results > 3.1 Mechanistic Validation",
          score: 0.97,
          snippet:
            "Intracellular Ca2+ transients peaked at 22 min and were abolished by nifedipine (10 µM)...",
        },
        {
          zotero_key: "KEY_DONE",
          title: "Fig 1. Osteogenic markers under 75 Hz PEMF",
          object_label: "figure_001",
          score: 0.89,
          snippet: "ALP activity bar plot confirming 75 Hz* peak vs Nifedipine blockade.",
        },
      ];
      v._renderSearchState();
    });

    // Col 3: Missing memory index + vectors not built recovery
    const app3 = new App(makeMockFiles(), VAULT_ROOT);
    makeFakePlugin(app3, snap);
    const c3 = grid.createDiv({ cls: "pf-doc-panel pf-doc-sidebar-shell" });
    c3.createDiv({ cls: "pf-doc-panel-label", text: "C. 索引未就绪恢复引导态" });
    const slot3 = c3.createDiv();
    const v3a = populateDashboardView(app3, slot3.createDiv(), snap, (v) => {
      v._currentMode = "global";
      v._renderModeHeader("global");
      v.renderSearchSection(v._contentEl);
      v._searchState = "missing-memory-index";
      v._renderSearchState();
    });
    const v3bMount = slot3.createDiv();
    const v3b = populateDashboardView(app3, v3bMount, snap, (v) => {
      v._currentMode = "global";
      v.renderSearchSection(v._contentEl);
      v._searchState = "vectors-not-built";
      v._renderSearchState();
    });
    void v3a;
    void v3b;
  }

  // ── Scene 07: PDF Annotator — Human + AI Layer + Simplified Popover ────────
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap, { pdfChanged: false });
    const { body } = createScene(
      "07-pdf-annotator-human-and-ai-layers",
      "07 · 内置侧车 PDF 阅读器：人类简化高亮 + [🤖 AI 批注层] + 3 级落地视觉形态",
      "人类划词浮窗已移除 5 枚意图按钮（仅留选色 + 备注）；AI 层区分精确虚线框（Stage 2a/2b）、图表框选（object）与页边括号（Stage 3）及 [✓ 采纳]",
      1380
    );
    const { mainSlot } = buildObsidianWorkspaceShell(body, {
      activeTabTitle: "PDF · 75 Hz PEMF Enhances...",
      activeRibbon: "base",
    });
    const pdfView = new PaperForgePdfView(new WorkspaceLeaf(), plugin as never);
    (pdfView as unknown as { app: App }).app = app;
    (pdfView as unknown as { contentEl: HTMLElement }).contentEl = mainSlot;
    (pdfView as unknown as { _scale: number })._scale = 1.05;
    await pdfView.setState({ paperKey: "KEY_DONE", page: 1 }, { history: false });
    const firstPage = pdfView.contentEl.querySelector(".pf-pdf-page") as HTMLElement;
    pdfView._openCreatePopover({
      anchorEl: firstPage,
      page: 1,
      rects: [[0.072, 0.302, 0.48, 0.34]],
      kind: "highlight",
      exactText: "PEMF stimulation at 75 Hz ± 5 µM markedly enhanced",
    });
    const popEl = pdfView.contentEl.querySelector(".pf-pdf-popover") as HTMLElement | null;
    if (popEl) {
      popEl.style.position = "absolute";
      popEl.style.right = "345px";
      popEl.style.top = "370px";
    }
    mainSlot.style.position = "relative";
  }

  // ── Scene 08: PDF Annotator Boundary States ────────────────────────────────
  {
    const snap = makeSnapshot("");
    const { body } = createScene(
      "08-pdf-annotator-provenance-and-empty-states",
      "08 · PDF 阅读器边界态：SHA-256 变更告警 + 关闭 AI 批注层 / 未绑定 PDF 空状态",
      "左：源文件哈希变更告警（⚠ 原 PDF 文件已变更）且关闭 [🤖 AI 批注层]；右：未打开/缺少规范 PDF 空提示态",
      1360
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-pdf-bounds" });

    // Left: SHA-256 changed + AI layer toggled OFF
    const appLeft = new App(makeMockFiles(), VAULT_ROOT);
    const pluginLeft = makeFakePlugin(appLeft, snap, { pdfChanged: true });
    const leftCard = grid.createDiv({ cls: "pf-doc-panel" });
    leftCard.createDiv({
      cls: "pf-doc-panel-label",
      text: "A. 原 PDF 变更告警 + [🤖 AI 批注层] 已关闭",
    });
    const leftMount = leftCard.createDiv();
    const pdfLeft = new PaperForgePdfView(new WorkspaceLeaf(), pluginLeft as never);
    (pdfLeft as unknown as { app: App }).app = appLeft;
    (pdfLeft as unknown as { contentEl: HTMLElement }).contentEl = leftMount;
    (pdfLeft as unknown as { _scale: number })._scale = 0.88;
    await pdfLeft.setState({ paperKey: "KEY_DONE", page: 1 }, { history: false });
    const aiToggleBtn = leftMount.querySelector(
      '[data-pf-testid="pdf-toggle-ai-layer"]'
    ) as HTMLButtonElement | null;
    aiToggleBtn?.click();

    // Right: Empty & Missing PDF states
    const appRight = new App(makeMockFiles(), VAULT_ROOT);
    const pluginRight = makeFakePlugin(appRight, snap);
    const rightCard = grid.createDiv({ cls: "pf-doc-panel" });
    rightCard.createDiv({
      cls: "pf-doc-panel-label",
      text: "B. 未选择文献空状态 & 无规范 PDF 提示",
    });
    const rEmptyMount = rightCard.createDiv({ cls: "pf-doc-subbox" });
    const pdfEmpty = new PaperForgePdfView(new WorkspaceLeaf(), pluginRight as never);
    (pdfEmpty as unknown as { app: App }).app = appRight;
    (pdfEmpty as unknown as { contentEl: HTMLElement }).contentEl = rEmptyMount;
    await pdfEmpty.onOpen();

    const rMissingMount = rightCard.createDiv({ cls: "pf-doc-subbox" });
    (pluginRight.getClient() as unknown as Record<string, unknown>).getPdfContext = async () => ({
      paper_id: "KEY_NOPDF",
      title: "Conference Abstract",
      pdf_abs_path: "",
      pdf_vault_rel: "",
      pdf_locator: "",
      is_vault_relative: false,
      pdf_sha256: "",
      page_count: 0,
      workspace_rel: "",
      note_rel_path: "",
      annotations: [],
    });
    const pdfMissing = new PaperForgePdfView(new WorkspaceLeaf(), pluginRight as never);
    (pdfMissing as unknown as { app: App }).app = appRight;
    (pdfMissing as unknown as { contentEl: HTMLElement }).contentEl = rMissingMount;
    await pdfMissing.setState({ paperKey: "KEY_NOPDF", page: 1 }, { history: false });
  }

  // ── Scene 09: Settings Control Center — All 6 UserStates + Maintenance ─────
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap);
    const envs = makeEnvelopes({ allReady: false, ocrRunning: true, memoryStale: true });
    const envsAlt = makeEnvelopes({ allReady: true });
    // Ensure all 6 UserStates are visible simultaneously:
    // installation=ready, library=setup_required, ocr=checking(progress)/action_required,
    // memory=detection_failed, agent=not_enabled
    envs.ocr = envsAlt.ocr; // checking + 2/5 progress
    envs.ocr.activity_state = "running";
    envs.ocr.activity_progress = { current: 2, total: 5 };

    const { body } = createScene(
      "09-settings-control-center-six-states",
      "09 · 设置控制中心：五大能力六态模型（Ready / Checking / Setup Required / Action Required / Not Enabled / Detection Failed）",
      "左：Control Center 五模块总览与进度活动行；右：Module Detail 故障/维护剖析与支持诊断复制",
      1280
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    const left = grid.createDiv({ cls: "pf-doc-panel pf-ob-settings-pane" });
    left.createDiv({
      cls: "pf-doc-panel-label",
      text: "A. Overview（Ready · Setup Required · Checking · Detection Failed · Not Enabled）",
    });
    const appNoAgent = new App(makeMockFiles(), `${VAULT_ROOT}/missing-agent`);
    const tabLeft = new PaperForgeSettingTab(appNoAgent, plugin as never);
    (tabLeft as unknown as { _capabilityState: Record<string, ProbeEnvelope> })._capabilityState =
      envs;
    tabLeft._renderControlCenter(left.createDiv());

    const right = grid.createDiv({ cls: "pf-doc-panel pf-ob-settings-pane" });
    right.createDiv({
      cls: "pf-doc-panel-label",
      text: "B. Action Required 详情 + 错误剖析与诊断卡（MaintenanceItem）",
    });
    const envActionReq = makeEnvelopes({ allReady: false, ocrRunning: false }).ocr;
    const tabRight = new PaperForgeSettingTab(app, plugin as never);
    (tabRight as unknown as { _capabilityState: Record<string, ProbeEnvelope> })._capabilityState =
      {
        ...envs,
        ocr: envActionReq,
      };
    tabRight._renderModuleDetailShell(right.createDiv(), "ocr");
    const maintBox = right.createDiv({ cls: "pf-doc-maint-sample" });
    renderErrorAnatomy(maintBox, {
      whatHappened: "历史扫描 PDF（KEY_FAILED）在 PaddleOCR 远端超时后未能生成结构化块。",
      impact: "该文献暂不参与全文混合检索；已处理好的其他 247 篇不受影响。",
      nextStep: "在高级 OCR 批量维护工作台检查原 PDF 或点击「重新 OCR」重试。",
      onCopyDiagnostic: () => {},
      copyLabel: t("problem_copy") || "复制诊断信息",
      copiedLabel: t("copied") || "已复制",
      whatLabel: t("problem_what_happened") || "发生了什么",
      impactLabel: t("problem_impact") || "影响：",
      nextLabel: t("problem_next") || "建议：",
    });
  }

  // ── Scene 10: Settings Setup Wizard — All 4 Stages ─────────────────────────
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap);
    plugin.settings._setup_complete = false;
    const { body } = createScene(
      "10-settings-setup-wizard-four-stages",
      "10 · 安装向导四阶段全览（Stage 1 基础环境 → Stage 2 连接文献库 → Stage 3 可选能力 → Stage 4 检查并开始）",
      "面向零基础科研人员的渐进引导向导，内置 Zotero / BBT 目录引导与多平台 Skill 部署",
      1280
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    for (const stage of [1, 2, 3, 4] as const) {
      const card = grid.createDiv({ cls: "pf-doc-panel pf-ob-settings-pane" });
      const stageNames: Record<number, string> = {
        1: "Stage 1 · 基础环境（Managed Runtime）",
        2: "Stage 2 · 连接文献库（Zotero & Better BibTeX）",
        3: "Stage 3 · 可选能力（OCR / 向量检索 / Agent 平台）",
        4: "Stage 4 · 检查并开始（Readiness Check）",
      };
      card.createDiv({ cls: "pf-doc-panel-label", text: stageNames[stage] });
      const tab = new PaperForgeSettingTab(app, plugin as never);
      (tab as unknown as { _capabilityState: Record<string, ProbeEnvelope> })._capabilityState =
        makeEnvelopes({ allReady: stage >= 2 });
      (tab as unknown as Record<string, unknown>)._attemptedProbes = new Set([
        "installation",
        "library",
        "ocr",
        "memory",
        "agent",
      ]);
      (tab as unknown as Record<string, unknown>)._runtimeStatus = {
        runtime_ready: stage > 1,
        version_matches_expected: true,
        runtime_version: "2.2.0",
        expected_version: "2.2.0",
      };
      (tab as unknown as Record<string, unknown>)._runtimeStatusVersion = "2.2.0";
      tab._setupStage = stage;
      tab._setupOptionals = { ocr: true, memory: true, agent: true };
      tab._renderSetupJourney(card.createDiv());
    }
  }

  // ── Scene 11: Settings OCR & Smart Retrieval Module Details ────────────────
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap);
    const { body } = createScene(
      "11-settings-ocr-and-memory-details",
      "11 · 设置模块详情：OCR（Option B 高级工作台入口）与 智能检索（Smart Retrieval）",
      "左：_renderOcrDetail 展示待处理提示、版本升级横幅、高级 OCR 批量维护工作台 ↗ 及接口配置；右：_renderMemoryDetail 展示 FTS5/vec0 与 Provider",
      1280
    );
    const grid = body.createDiv({ cls: "pf-doc-grid-2" });

    const left = grid.createDiv({ cls: "pf-doc-panel pf-ob-settings-pane" });
    left.createDiv({ cls: "pf-doc-panel-label", text: "A. OCR 模块详情（Option B 入口 + 端点配置）" });
    const tabOcr = new PaperForgeSettingTab(app, plugin as never);
    (tabOcr as unknown as { _capabilityState: Record<string, ProbeEnvelope> })._capabilityState =
      makeEnvelopes({ allReady: true, ocrRunning: false });
    tabOcr._renderOcrDetail(left.createDiv());

    const right = grid.createDiv({ cls: "pf-doc-panel pf-ob-settings-pane" });
    right.createDiv({
      cls: "pf-doc-panel-label",
      text: "B. 智能检索模块详情（SQLite FTS5 + vec0 + Provider）",
    });
    const tabMem = new PaperForgeSettingTab(app, plugin as never);
    (tabMem as unknown as { _capabilityState: Record<string, ProbeEnvelope> })._capabilityState =
      makeEnvelopes({ allReady: true });
    (tabMem as unknown as Record<string, unknown>).getClient = () => ({
      ...(plugin.getClient() as unknown as Record<string, unknown>),
      isOperationActive: () => false,
    });
    tabMem._renderMemoryDetail(right.createDiv());
  }

  // ── Scene 12: Secondary OCR Workspace & Modals (Option B) ──────────────────
  {
    const snap = makeSnapshot("");
    const app = new App(makeMockFiles(), VAULT_ROOT);
    const plugin = makeFakePlugin(app, snap);
    const { body } = createScene(
      "12-ocr-workspace-and-modals",
      "12 · Option B 二级维护面：高级 OCR 批量维护工作台、版本恢复对比、只读 OCR 诊断预览与孤儿清理弹窗",
      "已从左栏主入口撤出；日常科研走 Base + PDF，仅在批量重跑、版本回滚、排版核对或 Zotero 删后清理时按需进入",
      1320
    );
    const topBox = body.createDiv({ cls: "pf-doc-panel" });
    topBox.createDiv({
      cls: "pf-doc-panel-label",
      text: "A. OcrWorkspaceView（Batch 筛选 / 分页表 / 单篇诊断 / 批量操作栏）",
    });
    const wsMount = topBox.createDiv();
    const ocrWs = new OcrWorkspaceView(new WorkspaceLeaf(), plugin);
    (ocrWs as unknown as { app: App }).app = app;
    wsMount.appendChild(ocrWs.containerEl);
    await ocrWs.onOpen();
    (ocrWs as unknown as { selectedKey: string | null; _render: () => void }).selectedKey =
      "KEY_FAILED";
    (ocrWs as unknown as { _render: () => void })._render();

    // Modal 1: VersionRestoreModal (full width row so timeline + diff preview display cleanly)
    const m1 = body.createDiv({ cls: "pf-doc-panel" });
    m1.style.marginTop = "12px";
    m1.createDiv({ cls: "pf-doc-panel-label", text: "B. 版本恢复与对比弹窗（VersionRestoreModal）" });
    const m1Host = m1.createDiv({ cls: "pf-doc-modal-host" });
    const appM1 = new App(makeMockFiles(), VAULT_ROOT);
    (appM1 as unknown as { __modalHost: HTMLElement }).__modalHost = m1Host;
    new VersionRestoreModal(
      appM1,
      "KEY_DONE",
      [
        {
          label: "v3.2",
          created_at: "2026-11-18T10:00:00Z",
          source: "rebuild-v3",
          renderer_version: "v3.2",
          fulltext_size: 48200,
          source_path: "D:/ResearchVault/.paperforge/ocr/KEY_DONE/versions/v2/fulltext.md",
        },
        {
          label: "v3.1",
          created_at: "2026-10-02T08:15:00Z",
          source: "ocr-initial",
          renderer_version: "v3.1",
          fulltext_size: 47910,
          source_path: "D:/ResearchVault/.paperforge/ocr/KEY_DONE/versions/v1/fulltext.md",
        },
      ],
      "v3.2",
      "D:/ResearchVault/.paperforge/ocr/KEY_DONE/render/fulltext.md",
      async () => ({ label: "v3.1", current_path: "", provenance_persisted: true })
    ).open();

    const modalsGrid = body.createDiv({ cls: "pf-doc-grid-2" });
    modalsGrid.style.marginTop = "12px";

    // Modal 2: Read-only DiagnosticFulltextPreviewModal via OcrWorkspaceView._openFulltext
    const m2 = modalsGrid.createDiv({ cls: "pf-doc-panel" });
    m2.createDiv({
      cls: "pf-doc-panel-label",
      text: "C. 只读 OCR 排版诊断预览（DiagnosticFulltextPreviewModal）",
    });
    const m2Host = m2.createDiv({ cls: "pf-doc-modal-host" });
    const appM2 = new App(makeMockFiles(), VAULT_ROOT);
    (appM2 as unknown as { __modalHost: HTMLElement }).__modalHost = m2Host;
    (ocrWs as unknown as { app: App }).app = appM2;
    await (ocrWs as unknown as { _openFulltext: (k: string) => Promise<void> })._openFulltext(
      "KEY_DONE"
    );

    // Modal 3: PaperForgeOrphanModal
    const m3 = modalsGrid.createDiv({ cls: "pf-doc-panel" });
    m3.createDiv({ cls: "pf-doc-panel-label", text: "D. 孤儿工作区清理弹窗（PaperForgeOrphanModal）" });
    const m3Host = m3.createDiv({ cls: "pf-doc-modal-host" });
    const appM3 = new App(makeMockFiles(), VAULT_ROOT);
    (appM3 as unknown as { __modalHost: HTMLElement }).__modalHost = m3Host;
    new PaperForgeOrphanModal(
      appM3,
      [
        {
          key: "OLD_DEL01",
          title: "Removed Zotero Entry (Duplicate Preprint)",
          domain: "骨科",
        },
        {
          key: "OLD_DEL02",
          title: "Outdated Pilot Study Withdrawn from Collection",
          domain: "运动医学",
        },
      ],
      VAULT_ROOT,
      null
    ).open();
  }

  // Wait a couple ticks for async child components (LivingMemoryCard, credentialAvailable, etc.)
  await new Promise((r) => setTimeout(r, 120));
  (window as unknown as { __PF_SHOWCASE_READY__: boolean }).__PF_SHOWCASE_READY__ = true;
}

void renderAllScenes().catch((err) => {
  console.error("Showcase render failed:", err);
  (window as unknown as { __PF_SHOWCASE_ERROR__: string }).__PF_SHOWCASE_ERROR__ =
    err instanceof Error ? `${err.message}\n${err.stack}` : String(err);
});
