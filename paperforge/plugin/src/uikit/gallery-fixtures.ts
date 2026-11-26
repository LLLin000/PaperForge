/**
 * Self-contained realistic mock fixtures & mount helpers for the PaperForge
 * interactive UI Gallery. Works identically inside Obsidian (never mutating the
 * live vault or spawning Python subprocesses), standalone Chromium HTML, and
 * Vitest JSDOM.
 */

import { App, TFile, WorkspaceLeaf } from "obsidian";
import { DEFAULT_SETTINGS, type PaperForgeSettings } from "../constants";
import type {
  BasePaperRowDto,
  BaseTableSnapshotDto,
  PaperMemoryCardDto,
  PaperPdfContextDto,
  PdfAnnotationDto,
  ZoteroCollectionInfoDto,
} from "../client/paperforge-client";
import type { ProbeEnvelope } from "../client/probe-types";
import type { FilterField, SavedFilterView } from "./filter-bar";
import type { CommandSpec } from "./commands";

const VAULT_ROOT = "/mock-vault";
const ZOTERO_DIR = "/mock-zotero";

export function ensureObsidianElHelpers(): void {
  if (typeof HTMLElement === "undefined") return;
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (typeof proto.empty !== "function") {
    proto.empty = function (this: HTMLElement) {
      this.textContent = "";
    };
  }
  if (typeof proto.addClass !== "function") {
    proto.addClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c || "")
          .split(/\s+/)
          .filter(Boolean)) {
          this.classList.add(p);
        }
      }
    };
  }
  if (typeof proto.removeClass !== "function") {
    proto.removeClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c || "")
          .split(/\s+/)
          .filter(Boolean)) {
          this.classList.remove(p);
        }
      }
    };
  }
  if (typeof proto.toggleClass !== "function") {
    proto.toggleClass = function (
      this: HTMLElement,
      cls: string,
      force?: boolean
    ) {
      this.classList.toggle(cls, force);
    };
  }
  if (typeof proto.setText !== "function") {
    proto.setText = function (this: HTMLElement, text: string) {
      this.textContent = text;
    };
  }
  if (typeof proto.setAttr !== "function") {
    proto.setAttr = function (this: HTMLElement, k: string, v: string) {
      this.setAttribute(k, v);
    };
  }
  if (typeof proto.createEl !== "function") {
    proto.createEl = function (
      this: HTMLElement,
      tag: string,
      opts?:
        | string
        | {
            cls?: string;
            text?: string;
            type?: string;
            value?: string;
            placeholder?: string;
            title?: string;
            href?: string;
            attr?: Record<string, string>;
          },
      cb?: (el: HTMLElement) => void
    ) {
      const doc = this.ownerDocument || document;
      const el = doc.createElement(tag);
      const o = typeof opts === "string" ? { cls: opts } : opts;
      if (o?.cls) {
        for (const c of String(o.cls).split(/\s+/).filter(Boolean)) {
          el.classList.add(c);
        }
      }
      if (o?.text !== undefined) el.textContent = String(o.text);
      if (o?.type && "type" in el) (el as HTMLInputElement).type = o.type;
      if (o?.value !== undefined && "value" in el) {
        (el as HTMLInputElement).value = o.value;
      }
      if (o?.placeholder !== undefined && "placeholder" in el) {
        (el as HTMLInputElement).placeholder = o.placeholder;
      }
      if (o?.title) el.title = o.title;
      if (o?.href && "href" in el) (el as HTMLAnchorElement).href = o.href;
      if (o?.attr) {
        for (const [k, v] of Object.entries(o.attr)) {
          el.setAttribute(k, String(v));
        }
      }
      this.appendChild(el);
      cb?.(el);
      return el;
    };
  }
  if (typeof proto.createDiv !== "function") {
    proto.createDiv = function (
      this: HTMLElement,
      opts?: unknown,
      cb?: (el: HTMLElement) => void
    ) {
      return (
        this as unknown as {
          createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
        }
      ).createEl("div", opts, cb);
    };
  }
  if (typeof proto.createSpan !== "function") {
    proto.createSpan = function (
      this: HTMLElement,
      opts?: unknown,
      cb?: (el: HTMLElement) => void
    ) {
      return (
        this as unknown as {
          createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
        }
      ).createEl("span", opts, cb);
    };
  }
}

export function makeGallerySnapshot(): BaseTableSnapshotDto {
  const rows: Record<string, BasePaperRowDto> = {
    KEY_DONE: {
      zotero_key: "KEY_DONE",
      title:
        "75 Hz PEMF Enhances Osteogenic Differentiation via L-Type Ca2+ Channels",
      first_author: "Zhang W.",
      year: "2025",
      journal: "Biomaterials",
      impact_factor: "14.0",
      impact_factor_source: "JCR 2024",
      journal_partition: "Q1",
      domain: "骨科",
      collections: ["骨科", "电磁刺激"],
      has_pdf: true,
      do_ocr: true,
      analyze: true,
      ocr_status: "done",
      deep_reading_status: "complete",
      main_note_path: "Resources/Literature/骨科/KEY_DONE/KEY_DONE.md",
      user_ann_count: 5,
      agent_ann_count: 2,
      memory_facet_count: 5,
      memory_updated_at: "2026-11-18T11:20:00Z",
      needs_diagnostic: false,
    },
    KEY_PROC: {
      zotero_key: "KEY_PROC",
      title: "PIEZO1 Mechanosensor Mediates Synovial Macrophage Polarization",
      first_author: "Chen R.",
      year: "2025",
      journal: "Ann. Rheum. Dis.",
      impact_factor: "20.3",
      journal_partition: "Q1",
      domain: "骨科",
      collections: ["骨科"],
      has_pdf: true,
      do_ocr: true,
      analyze: false,
      ocr_status: "processing",
      deep_reading_status: "pending",
      main_note_path: "Resources/Literature/骨科/KEY_PROC/KEY_PROC.md",
      user_ann_count: 1,
      agent_ann_count: 0,
      memory_facet_count: 2,
      memory_updated_at: "2026-11-18T09:10:00Z",
      needs_diagnostic: false,
    },
    KEY_PENDING: {
      zotero_key: "KEY_PENDING",
      title: "Subchondral Bone Remodeling Under Cyclic Compressive Loading",
      first_author: "Li H.",
      year: "2024",
      journal: "Osteoarthritis Cartilage",
      impact_factor: "7.2",
      journal_partition: "Q1",
      domain: "骨科",
      collections: ["骨科"],
      has_pdf: true,
      do_ocr: false,
      analyze: false,
      ocr_status: "pending",
      deep_reading_status: "pending",
      main_note_path: "Resources/Literature/骨科/KEY_PENDING/KEY_PENDING.md",
      user_ann_count: 0,
      agent_ann_count: 0,
      memory_facet_count: 0,
      memory_updated_at: "",
      needs_diagnostic: false,
    },
    KEY_INCOMPLETE: {
      zotero_key: "KEY_INCOMPLETE",
      title: "Biphasic Calcium Phosphate Scaffold Vascularization Kinetics",
      first_author: "Liu K.",
      year: "2023",
      journal: "Acta Biomater.",
      impact_factor: "9.4",
      journal_partition: "Q1",
      domain: "生物材料",
      collections: ["生物材料"],
      has_pdf: true,
      do_ocr: true,
      analyze: false,
      ocr_status: "done_incomplete",
      deep_reading_status: "pending",
      main_note_path:
        "Resources/Literature/生物材料/KEY_INCOMPLETE/KEY_INCOMPLETE.md",
      user_ann_count: 2,
      agent_ann_count: 1,
      memory_facet_count: 1,
      memory_updated_at: "2026-11-17T14:00:00Z",
      needs_diagnostic: true,
    },
    KEY_FAILED: {
      zotero_key: "KEY_FAILED",
      title: "Rotator Cuff Tendon-to-Bone Healing in Aged Rabbit Model",
      first_author: "Zhou Y.",
      year: "2022",
      journal: "Am. J. Sports Med.",
      impact_factor: "4.8",
      journal_partition: "Q1",
      domain: "运动医学",
      collections: ["运动医学"],
      has_pdf: true,
      do_ocr: true,
      analyze: false,
      ocr_status: "failed",
      deep_reading_status: "pending",
      main_note_path: "Resources/Literature/运动医学/KEY_FAILED/KEY_FAILED.md",
      user_ann_count: 0,
      agent_ann_count: 0,
      memory_facet_count: 0,
      memory_updated_at: "",
      needs_diagnostic: true,
    },
    KEY_NOPDF: {
      zotero_key: "KEY_NOPDF",
      title: "Early ACL Reconstruction Timing Multicenter Cohort Protocol",
      first_author: "Wang T.",
      year: "2021",
      journal: "KSSTA",
      impact_factor: "3.3",
      journal_partition: "Q2",
      domain: "运动医学",
      collections: ["运动医学"],
      has_pdf: false,
      do_ocr: false,
      analyze: false,
      ocr_status: "none",
      deep_reading_status: "pending",
      main_note_path: "Resources/Literature/运动医学/KEY_NOPDF/KEY_NOPDF.md",
      user_ann_count: 0,
      agent_ann_count: 0,
      memory_facet_count: 0,
      memory_updated_at: "",
      needs_diagnostic: false,
    },
  };
  return { seq: 42, updated_at: "2026-11-25T10:00:00Z", rows };
}

export function makeGalleryAnnotations(): PdfAnnotationDto[] {
  return [
    {
      ann_id: "ann_ai_ev",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "highlight",
      color: "purple",
      intent: "evidence",
      author: "agent",
      exact_text:
        "Nifedipine (10 µM) abolished downstream ERK phosphorylation at 22 min",
      comment:
        "AI 提炼核心机制证据：证实 L-type Ca2+ 通道是 75 Hz PEMF 的必需上游开关 [p.1 · Fig 1]。",
      tags: ["mechanism", "ca2+"],
      rects: [
        [0.062, 0.302, 0.479, 0.33],
        [0.062, 0.347, 0.298, 0.375],
      ],
      section_path: "Results > 3.1 Parameters",
      block_id: "blk_02",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "e3b0c442",
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
      exact_text:
        "PEMF stimulation at 75 Hz (1.2 mT) enhanced early osteogenic differentiation",
      comment: "对比我们动物实验参数（50 Hz vs 75 Hz）时重点复核。",
      tags: ["parameters"],
      rects: [
        [0.062, 0.212, 0.475, 0.24],
        [0.062, 0.257, 0.357, 0.285],
      ],
      section_path: "Results > 3.1 Parameters",
      block_id: "blk_01",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "e3b0c442",
      created_at: "2026-11-18T09:10:00Z",
      updated_at: "2026-11-18T09:10:00Z",
      provenance_status: "verified",
    },
    {
      ann_id: "ann_u_arrow",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "shape",
      color: "red",
      intent: "general",
      author: "user",
      exact_text: "",
      comment: "Fig 1 峰值出现在 75 Hz 组",
      tags: [],
      rects: [[0.58, 0.24, 0.75, 0.37]],
      style: {
        shape_type: "arrow",
        stroke_color: "#d64545",
        stroke_width: 2.5,
        points: [
          [0.58, 0.24],
          [0.74, 0.36],
        ],
      },
      section_path: "Results > Fig. 1",
      block_id: "blk_fig1",
      figure_id: "figure_001",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "e3b0c442",
      created_at: "2026-11-18T09:16:00Z",
      updated_at: "2026-11-18T09:16:00Z",
      provenance_status: "verified",
    },
    {
      ann_id: "ann_u_rect",
      paper_id: "KEY_DONE",
      page: 1,
      kind: "shape",
      color: "purple",
      intent: "general",
      author: "user",
      exact_text: "",
      comment: "",
      tags: [],
      rects: [[0.71, 0.29, 0.79, 0.5]],
      style: {
        shape_type: "rect",
        stroke_color: "#5b45c9",
        fill_color: "transparent",
        stroke_width: 2,
      },
      section_path: "Results > Fig. 1",
      block_id: "blk_fig1",
      figure_id: "figure_001",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "e3b0c442",
      created_at: "2026-11-18T09:18:00Z",
      updated_at: "2026-11-18T09:18:00Z",
      provenance_status: "verified",
    },
  ];
}

export function makeGalleryMemoryCard(populated: boolean): PaperMemoryCardDto {
  if (!populated) {
    return {
      paper_id: "KEY_PENDING",
      updated_at: "",
      facet_count: 0,
      facets: [],
    };
  }
  return {
    paper_id: "KEY_DONE",
    updated_at: "2026-11-18T11:20:00Z",
    facet_count: 5,
    facets: [
      {
        facet: "question",
        label: "核心科学问题",
        content:
          "75 Hz 脉冲电磁场是否经 L 型钙通道调控成骨早期的 ERK1/2 级联 [p.1]。",
        revision: 3,
        updated_at: "2026-11-18T11:20:00Z",
      },
      {
        facet: "method",
        label: "实验设计",
        content:
          "BMSCs 原代成骨诱导 + Nifedipine (10 µM) 通道阻断对照，n = 6 [p.2]。",
        revision: 2,
        updated_at: "2026-11-18T10:15:00Z",
      },
      {
        facet: "finding",
        label: "关键结论",
        content:
          "75 Hz 组第 7 天 ALP 活性最高，22 min 时胞内 Ca2+ 瞬变显著峰值 [Fig. 1]。",
        revision: 3,
        updated_at: "2026-11-18T11:20:00Z",
      },
      {
        facet: "limitation",
        label: "局限与质疑",
        content: "缺乏动物体内负重骨缺损模型验证，仅测试体外单核刺激条件。",
        revision: 1,
        updated_at: "2026-11-18T09:50:00Z",
      },
      {
        facet: "connection",
        label: "课题关联",
        content: "可直接支撑我们水凝胶支架联合电磁场的频率选型依据。",
        revision: 2,
        updated_at: "2026-11-18T11:18:00Z",
      },
    ],
  };
}

export function makeGalleryEnvelopes(opts?: {
  allReady?: boolean;
  ocrRunning?: boolean;
  memoryStale?: boolean;
}): Record<string, ProbeEnvelope> {
  const now = "2026-11-25T10:00:00Z";
  const allReady = opts?.allReady ?? true;
  const ocrRunning = opts?.ocrRunning ?? false;
  const memoryStale = opts?.memoryStale ?? false;

  const noAction = { primary: null };
  return {
    installation: {
      schema_version: 2,
      module: "installation",
      capability_state: "ready",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "ok",
      reason: {
        code: "installation.ready",
        text: "Python 3.11 托管引擎 v2.2.0 与控制守护进程运行正常。",
      },
      action: noAction,
      notices: [],
      user_state: "ready",
      capability_kind: "required",
      maintenance_eligible: false,
      user_visible_failure: false,
      user_impact: null,
      updated_at: now,
      ttl_seconds: 300,
    },
    library: {
      schema_version: 2,
      module: "library",
      capability_state: allReady ? "ready" : "missing_input",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: allReady ? "ok" : "warning",
      reason: {
        code: allReady ? "library.ready" : "library.setup_required",
        text: allReady
          ? "已直连 Zotero SQLite（6 篇示例文献 · 3 个学科集合）。"
          : "需选择 Zotero 数据目录以开启本地零代码文献同步。",
      },
      action: allReady
        ? noAction
        : {
            primary: {
              action_id: "library.sync",
              verb: "sync",
              label: "立即配置目录",
              availability: "available",
              safety_class: "safe",
              preservation_facts: [],
              replacement_facts: [],
              interruptible: false,
              confirmation_required: false,
              confirmation_prompt: null,
              scope: "library",
              scope_count: 1,
            },
          },
      notices: [],
      user_state: allReady ? "ready" : "setup_required",
      capability_kind: "required",
      maintenance_eligible: !allReady,
      user_visible_failure: false,
      user_impact: allReady ? null : "尚未连接 Zotero 数据库。",
      updated_at: now,
      ttl_seconds: 300,
    },
    ocr: {
      schema_version: 2,
      module: "ocr",
      capability_state: allReady ? "ready" : "limited",
      activity_state: ocrRunning ? "running" : "idle",
      activity_label: ocrRunning ? "正在队列解析全文 (2/5)" : null,
      activity_progress: ocrRunning ? { current: 2, total: 5 } : null,
      severity: allReady ? "ok" : "warning",
      reason: {
        code: allReady ? "ocr.ready" : "ocr.action_required",
        text: allReady
          ? "PaddleOCR 结构化引擎就绪；1 篇历史文献待局部补全。"
          : "检测到 1 篇扫描 PDF 解析异常，建议打开 OCR 批量工作台重试。",
      },
      action: {
        primary: {
          action_id: "ocr.run",
          verb: "run",
          label: "解析待处理文献",
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
      user_state: ocrRunning
        ? "checking"
        : allReady
          ? "ready"
          : "action_required",
      capability_kind: "optional",
      maintenance_eligible: true,
      user_visible_failure: !allReady,
      user_impact: allReady ? null : "有失败文献未生成结构化正文。",
      updated_at: now,
      ttl_seconds: 300,
    },
    memory: {
      schema_version: 2,
      module: "memory",
      capability_state: memoryStale ? "needs_action" : "ready",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: memoryStale ? "error" : "ok",
      reason: {
        code: memoryStale ? "memory.probe_error" : "memory.ready",
        text: memoryStale
          ? "SQLite FTS5 检测响应超时，请点击重建索引。"
          : "FTS5 + vec0 混合检索引擎就绪（248 篇 · 6,420 单元）。",
      },
      action: noAction,
      notices: [],
      user_state: memoryStale ? "detection_failed" : "ready",
      capability_kind: "optional",
      maintenance_eligible: memoryStale,
      user_visible_failure: memoryStale,
      user_impact: memoryStale ? "全文混合检索暂不可用。" : null,
      updated_at: now,
      ttl_seconds: 300,
      details: {
        api_key_configured: true,
        build_state: { status: "idle" },
        paper_count_db: 248,
        paper_count_index: 248,
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
        text: "尚未向外部 AI 编辑器部署 PaperForge Skills（可选）。",
      },
      action: noAction,
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

export interface GalleryMockEnv {
  app: App;
  snapshot: BaseTableSnapshotDto;
  envelopes: Record<string, ProbeEnvelope>;
  annotations: PdfAnnotationDto[];
  collections: ZoteroCollectionInfoDto[];
  plugin: Record<string, unknown>;
}

export function createGalleryMockEnv(opts?: {
  populatedMemory?: boolean;
  pdfChanged?: boolean;
  ocrRunning?: boolean;
  allReady?: boolean;
  memoryStale?: boolean;
}): GalleryMockEnv {
  ensureObsidianElHelpers();
  const snapshot = makeGallerySnapshot();
  const annotations = makeGalleryAnnotations();
  if (opts?.pdfChanged) {
    for (const ann of annotations) ann.provenance_status = "changed";
  }
  const envelopes = makeGalleryEnvelopes(opts);
  const ocrRunning = Boolean(opts?.ocrRunning);
  const collections: ZoteroCollectionInfoDto[] = [
    {
      key: "COL_ORTHO",
      name: "骨科",
      path: "骨科",
      top_level: true,
      direct_item_count: 86,
      item_count: 86,
    },
    {
      key: "COL_SPORTS",
      name: "运动医学",
      path: "运动医学",
      top_level: true,
      direct_item_count: 34,
      item_count: 34,
    },
    {
      key: "COL_BIOMAT",
      name: "生物材料与水凝胶",
      path: "生物材料与水凝胶",
      top_level: true,
      direct_item_count: 22,
      item_count: 22,
    },
  ];

  // Safe sandboxed App clone so clicks inside Gallery never touch live vault
  const mockApp = {
    vault: {
      adapter: { basePath: VAULT_ROOT, getResourcePath: (p: string) => p },
      getConfig: (k?: string) => (k === "theme" ? "obsidian" : "zh"),
      getAbstractFileByPath: (p: string) =>
        new (TFile as unknown as new (p?: string) => TFile)(p),
      getMarkdownFiles: () => [],
      cachedRead: async () => "# 75 Hz PEMF Osteogenesis\n\nGallery preview.",
      read: async () => "# 75 Hz PEMF Osteogenesis\n\nGallery preview.",
      on: () => ({}),
      offref: () => {},
    },
    workspace: {
      on: () => ({}),
      offref: () => {},
      getLeavesOfType: () => [],
      getActiveViewOfType: () => null,
      getActiveFile: () => null,
      getRightLeaf: () =>
        new (WorkspaceLeaf as unknown as new () => WorkspaceLeaf)(),
      getLeaf: () =>
        new (WorkspaceLeaf as unknown as new () => WorkspaceLeaf)(),
      revealLeaf: async () => {},
      openLinkText: async () => {},
      trigger: () => {},
    },
    metadataCache: {
      getFileCache: () => ({ frontmatter: {} }),
      on: () => ({}),
      offref: () => {},
    },
    plugins: { plugins: {} as Record<string, unknown> },
    keymap: { pushScope: () => {}, popScope: () => {} },
    commands: {
      commands: {},
      executeCommandById: () => false,
    },
  } as unknown as App;

  const settings: PaperForgeSettings = {
    ...DEFAULT_SETTINGS,
    vault_path: VAULT_ROOT,
    system_dir: ".paperforge",
    resources_dir: "Resources",
    literature_dir: "Resources/Literature",
    base_dir: "Resources/Literature/Base",
    zotero_data_dir: ZOTERO_DIR,
    domain_mode: "per_collection",
    agent_platform: "claude",
    language: "zh",
    _paddleocr_configured: true,
    _vector_db_configured: true,
    _setup_complete: true,
  };

  const client = {
    isOperationActive: () => ocrRunning,
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
    getMemoryCard: async (key: string) =>
      makeGalleryMemoryCard(opts?.populatedMemory ?? key === "KEY_DONE"),
    getPdfContext: async (key: string): Promise<PaperPdfContextDto> => ({
      paper_id: key,
      title: snapshot.rows[key]?.title || "75 Hz PEMF Osteogenesis",
      pdf_abs_path:
        key === "KEY_NOPDF" ? "" : `${ZOTERO_DIR}/storage/${key}/paper.pdf`,
      pdf_vault_rel: "",
      pdf_locator: key === "KEY_NOPDF" ? "" : `storage:${key}/paper.pdf`,
      is_vault_relative: false,
      pdf_sha256: "e3b0c442",
      page_count: key === "KEY_NOPDF" ? 0 : 12,
      workspace_rel: `Resources/Literature/骨科/${key}`,
      note_rel_path: `Resources/Literature/骨科/${key}/${key}.md`,
      annotations: key === "KEY_NOPDF" ? [] : annotations,
    }),
    listAnnotations: async () => annotations,
    addAnnotation: async (
      paper_id: string,
      input: Record<string, unknown>
    ) => ({
      ann_id: "ann_new",
      paper_id,
      tags: [],
      created_at: "2026-11-25T10:00:00Z",
      updated_at: "2026-11-25T10:00:00Z",
      provenance_status: "verified",
      ...input,
    }),
    updateAnnotation: async (
      _k: string,
      id: string,
      patch: Record<string, unknown>
    ) => ({
      ...(annotations.find((a) => a.ann_id === id) ?? annotations[0]),
      ...patch,
    }),
    deleteAnnotation: async (_k: string, id: string) => ({
      deleted: true,
      ann_id: id,
    }),
    promoteAnnotation: async () => ({ promoted: true }),
    adoptAnnotation: async (_k: string, id: string) =>
      annotations.find((a) => a.ann_id === id) ?? annotations[0],
    clearAgentAnnotations: async () => ({
      paper_id: "KEY_DONE",
      deleted_count: 1,
      deleted_ids: ["ann_ai_ev"],
    }),
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
      return envelopes[mod] ?? envelopes.ocr;
    },
    queryOcrPapers: async () => [
      {
        key: "KEY_DONE",
        title: snapshot.rows.KEY_DONE.title,
        status: "done",
        version: "v3.2",
        authors: "Zhang W.",
        year: "2025",
        pages: 12,
        can_rebuild: true,
        can_redo: true,
        recommended_action: "none",
        fulltext_path: ".paperforge/ocr/KEY_DONE/render/fulltext.md",
      },
      {
        key: "KEY_PROC",
        title: snapshot.rows.KEY_PROC.title,
        status: "processing",
        version: "v3.2",
        authors: "Chen R.",
        year: "2025",
        pages: 14,
        can_rebuild: false,
        can_redo: false,
        recommended_action: "none",
        fulltext_path: "",
      },
      {
        key: "KEY_INCOMPLETE",
        title: snapshot.rows.KEY_INCOMPLETE.title,
        status: "done_incomplete",
        version: "v3.1",
        authors: "Liu K.",
        year: "2023",
        pages: 10,
        can_rebuild: true,
        can_redo: true,
        recommended_action: "rebuild",
        fulltext_path: ".paperforge/ocr/KEY_INCOMPLETE/render/fulltext.md",
      },
      {
        key: "KEY_FAILED",
        title: snapshot.rows.KEY_FAILED.title,
        status: "failed",
        version: "v2.8",
        authors: "Zhou Y.",
        year: "2022",
        pages: 9,
        can_rebuild: true,
        can_redo: true,
        recommended_action: "retry",
        fulltext_path: "",
      },
      {
        key: "KEY_PENDING",
        title: snapshot.rows.KEY_PENDING.title,
        status: "pending",
        version: "",
        authors: "Li H.",
        year: "2024",
        pages: 8,
        can_rebuild: false,
        can_redo: false,
        recommended_action: "run",
        fulltext_path: "",
      },
    ],
    readDiagnosticFulltext: async (key: string) => ({
      paper_id: key,
      content:
        "# 3.1 PEMF Stimulation Parameters\n\n" +
        "[p.1 · blk_01 · conf=0.98]\n" +
        "PEMF stimulation at 75 Hz markedly enhanced osteogenic differentiation.",
      truncated: false,
      total_lines: 4,
      total_chars: 180,
    }),
    describeAction: async (actionId: string) => ({
      action_id: actionId,
      availability: "available",
      confirmation: "not_required",
    }),
    configSet: async () => ({}),
    embedStatus: async () => ({
      model: "text-embedding-3-small",
      mode: "requests",
      deps_installed: true,
      body_chunk_count: 5840,
      object_chunk_count: 580,
      total_chunks: 6420,
      build_state: { status: "idle" },
    }),
    embedTestConnection: async () => ({
      model: "BAAI/bge-m3",
      base_url: "https://api.siliconflow.cn/v1",
      dimension: 1024,
      latency_ms: 142,
    }),
    embedListModels: async (baseUrl?: string) => {
      const isOllama = String(baseUrl || "").includes("11434");
      return isOllama
        ? {
            source: "ollama",
            base_url: "http://127.0.0.1:11434/v1",
            reachable: true,
            models: ["bge-m3:latest", "nomic-embed-text:latest", "qwen3:8b"],
            embedding_models: ["bge-m3:latest", "nomic-embed-text:latest"],
          }
        : {
            source: "openai_compatible",
            base_url: baseUrl || "https://custom.example/v1",
            reachable: true,
            models: ["Pro/BAAI/bge-m3", "text-embedding-3-small", "gpt-4o"],
            embedding_models: ["Pro/BAAI/bge-m3", "text-embedding-3-small"],
          };
    },
    memoryStatus: async () => ({
      paper_count_db: 248,
      fresh: true,
      needs_rebuild: false,
    }),
    versionsShow: async () => ({
      versions: [],
      current_label: "v3.2",
      current_path: "",
    }),
    versionsBackups: async () => [],
    zoteroDetect: async () => ({
      found: true,
      zotero_dir: ZOTERO_DIR,
      total_papers: 142,
      collections,
    }),
  };

  const baseFilters = new Map<string, Record<string, unknown>>();
  const plugin: Record<string, unknown> = {
    app: mockApp,
    manifest: { id: "paperforge", version: "2.2.0", name: "PaperForge" },
    settings,
    agentPlatformChoices: ["opencode", "claude", "codex", "cursor", "gemini"],
    _embedStatusCache: {},
    _ocrProgress: ocrRunning
      ? { current: 2, total: 5, key: "KEY_PROC" }
      : undefined,
    getClient: () => client,
    getBaseSnapshotCache: () => snapshot,
    getBaseFilters: (k: string) => baseFilters.get(k) ?? {},
    setBaseFilters: (k: string, v: Record<string, unknown>) => {
      baseFilters.set(k, v);
    },
    refreshBaseSnapshot: async () => snapshot,
    getActiveBackgroundTasks: () =>
      ocrRunning
        ? [
            {
              kind: "ocr" as const,
              label: "正在解析全文",
              current: 2,
              total: 5,
              key: "KEY_PROC",
            },
          ]
        : [],
    isOcrRunningForKey: (k: string) => ocrRunning && k === "KEY_PROC",
    openPaperPdf: async () => {},
    openPaperSplitReading: async () => {},
    requestOcrRun: async () => {},
    triggerManualSync: () => {},
    openOcrDiagnostic: () => {},
    openModuleSettings: () => true,
    openSetupJourney: () => true,
    applyUiThemeMode: () => {},
    saveSettings: async () => {},
  };
  (
    mockApp as unknown as { plugins: { plugins: Record<string, unknown> } }
  ).plugins.plugins["paperforge"] = plugin;

  return {
    app: mockApp,
    snapshot,
    envelopes,
    annotations,
    collections,
    plugin,
  };
}

export function makeGalleryBaseEntries(
  snapshot: BaseTableSnapshotDto,
  keys: string[]
) {
  const priorityByKey: Record<string, string> = {
    KEY_DONE: "核心精读",
    KEY_PROC: "高优待读",
    KEY_PENDING: "待筛查",
    KEY_INCOMPLETE: "待补全",
    KEY_FAILED: "待复核",
    KEY_NOPDF: "仅摘要",
  };
  return keys.map((k) => {
    const row = snapshot.rows[k];
    const propMap: Record<string, string> = {
      "note.zotero_key": k,
      "note.domain": row?.domain || "",
      "note.year": row?.year || "",
      "note.journal": row?.journal || "",
      "note.impact_factor": row?.impact_factor || "",
      "note.authors": row?.first_author || "",
      "note.priority": priorityByKey[k] || "",
    };
    return {
      file: new (TFile as unknown as new (p?: string) => TFile)(
        row?.main_note_path || `${k}.md`
      ),
      getValue: (propId: string) =>
        propId in propMap
          ? { data: propMap[propId], toString: () => propMap[propId] }
          : null,
    };
  });
}

export const GALLERY_FILTER_FIELDS: FilterField[] = [
  {
    key: "domain",
    label: "研究领域",
    options: [
      { value: "骨科", label: "骨科" },
      { value: "生物材料", label: "生物材料" },
      { value: "运动医学", label: "运动医学" },
    ],
  },
  {
    key: "ocr_status",
    label: "解析状态",
    options: [
      { value: "done", label: "已解析 done" },
      { value: "processing", label: "解析中 processing" },
      { value: "done_incomplete", label: "部分缺失 done_incomplete" },
      { value: "failed", label: "解析异常 failed" },
      { value: "pending", label: "未解析 pending" },
    ],
  },
  {
    key: "year",
    label: "发表年份",
    options: [
      { value: "2025", label: "2025" },
      { value: "2024", label: "2024" },
      { value: "2023", label: "2023" },
      { value: "2022", label: "2022" },
    ],
  },
];

export const GALLERY_SAVED_VIEWS: SavedFilterView[] = [
  { id: "all", label: "全部文献", filters: [] },
  {
    id: "q1_ortho",
    label: "骨科已解析",
    filters: [
      { fieldKey: "domain", value: "骨科" },
      { fieldKey: "ocr_status", value: "done" },
    ],
  },
  {
    id: "needs_fix",
    label: "需处理异常",
    filters: [{ fieldKey: "ocr_status", value: "failed" }],
  },
];

export function buildGalleryDemoCommands(
  onNotify: (msg: string) => void
): CommandSpec[] {
  return [
    {
      id: "sync-library",
      title: "同步 Zotero 文献库",
      category: "文献库",
      defaultShortcut: "Mod+Shift+S",
      run: () => onNotify("触发同步命令：sync-library"),
    },
    {
      id: "open-quick-switcher",
      title: "快速跳转文献或插入引用",
      category: "导航",
      defaultShortcut: "Mod+Alt+P",
      run: () => onNotify("已模拟打开快速检索面板"),
    },
    {
      id: "run-ocr-batch",
      title: "解析当前筛选文献全文 (OCR)",
      category: "OCR",
      defaultShortcut: "Mod+Shift+O",
      run: () => onNotify("已提交批量 OCR 解析任务"),
    },
    {
      id: "toggle-gallery-theme",
      title: "打开 UI 设计系统画廊",
      category: "系统",
      defaultShortcut: "Mod+Shift+G",
      run: () => onNotify("当前已处于 PaperForge UI 画廊"),
    },
  ];
}

export function createMockPdfDocForObsidian() {
  return {
    numPages: 12,
    async getPage(pageNumber: number) {
      return {
        getViewport: ({ scale }: { scale: number }) => ({
          width: 560 * scale,
          height: 490 * scale,
          transform: [scale, 0, 0, scale, 0, 0],
        }),
        render: ({
          canvasContext,
          viewport,
        }: {
          canvasContext: CanvasRenderingContext2D;
          viewport: { width: number; height: number };
        }) => ({
          promise: (async () => {
            if (
              !canvasContext ||
              typeof canvasContext.fillRect !== "function"
            ) {
              return;
            }
            const s = Math.max(0.25, viewport.width / 560);
            canvasContext.save();
            canvasContext.scale(s, s);
            canvasContext.fillStyle = "#ffffff";
            canvasContext.fillRect(0, 0, 560, 490);
            canvasContext.fillStyle = "#64748b";
            canvasContext.font = "10px Inter, system-ui, sans-serif";
            canvasContext.fillText(
              `Biomaterials (2025) · p.${pageNumber}`,
              36,
              28
            );
            canvasContext.fillStyle = "#0f172a";
            canvasContext.font = "bold 14px Inter, system-ui, sans-serif";
            canvasContext.fillText(
              "75 Hz PEMF Enhances Osteogenic Differentiation via L-Type Ca2+",
              36,
              56
            );
            canvasContext.fillStyle = "#1e293b";
            canvasContext.font = "10.5px Georgia, serif";
            const lines = [
              "3.1 Stimulation Parameters",
              "PEMF stimulation at 75 Hz (1.2 mT) enhanced",
              "early osteogenic differentiation and Ca2+ influx.",
              "Nifedipine (10 µM) abolished downstream ERK",
              "phosphorylation at 22 min across n = 6 donors.",
              "ALP activity peaked at day 7 compared to sham",
              "and 15 Hz controls (p < 0.01, ANOVA + Tukey).",
            ];
            let y = 92;
            for (const line of lines) {
              canvasContext.fillText(line, 36, y);
              y += 22;
            }
            canvasContext.strokeStyle = "#cbd5e1";
            canvasContext.strokeRect(290, 92, 232, 168);
            canvasContext.fillStyle = "#5b45c9";
            canvasContext.fillRect(410, 128, 28, 102);
            canvasContext.restore();
          })(),
        }),
        getTextContent: async () => ({
          items: [
            {
              str: "PEMF stimulation at 75 Hz enhanced osteogenesis",
              transform: [1, 0, 0, 11, 36, 360],
            },
          ],
        }),
      };
    },
    async getOutline() {
      return [
        { title: "1. Introduction", dest: null, items: [] },
        { title: "2. Methods", dest: null, items: [] },
        { title: "3. Results · Fig. 1", dest: null, items: [] },
      ];
    },
    async destroy() {},
  };
}
