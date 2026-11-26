/**
 * Embedding provider presets + live interactive Domain mapping preview card.
 *
 * Keeps beginner onboarding 100% jargon-free:
 * 1. Researchers choose a preset provider (SiliconFlow / DashScope / Zhipu / OpenAI / Ollama)
 *    instead of typing URLs or choosing SDK vs requests internals.
 * 2. Live animated SVG/DOM tree diagram visualizes Option A (per Zotero top folder) vs
 *    Option B (single unified library + Base toolbar pills) using their actual checked folders.
 */

import { setPfIcon } from "./icons";

export interface EmbeddingProviderPreset {
  id: string;
  shortLabelZh: string;
  shortLabelEn: string;
  labelZh: string;
  labelEn: string;
  traitZh: string;
  traitEn: string;
  baseUrl: string;
  model: string;
  models: readonly string[];
  dimensionsHint: string;
  signupUrl?: string;
}

export const EMBEDDING_PRESETS: readonly EmbeddingProviderPreset[] = [
  {
    id: "siliconflow",
    shortLabelZh: "硅基流动 · 推荐",
    shortLabelEn: "SiliconFlow · Recommended",
    labelZh: "硅基流动 SiliconFlow（国内直连 · 永久免费额度 · 推荐）",
    labelEn: "SiliconFlow (China direct · BAAI/bge-m3 · Recommended)",
    traitZh: "国内直连 · 含永久免费额度 · 中英双语文献首选",
    traitEn: "China direct · Free tier · Best for bilingual papers",
    baseUrl: "https://api.siliconflow.cn/v1",
    model: "BAAI/bge-m3",
    models: [
      "BAAI/bge-m3",
      "Qwen/Qwen3-Embedding-8B",
      "BAAI/bge-large-zh-v1.5",
    ],
    dimensionsHint: "1024",
    signupUrl: "https://cloud.siliconflow.cn/account/ak",
  },
  {
    id: "dashscope",
    shortLabelZh: "阿里云百炼",
    shortLabelEn: "DashScope",
    labelZh: "阿里云百炼 DashScope（国内直连 · text-embedding-v4）",
    labelEn: "Alibaba DashScope (text-embedding-v4)",
    traitZh: "国内直连 · 新人试用额度 · 高校/企业网络稳定",
    traitEn: "China direct · Trial credits · Reliable academic network",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: "text-embedding-v4",
    models: ["text-embedding-v4", "text-embedding-v3"],
    dimensionsHint: "1024",
    signupUrl: "https://bailian.console.aliyun.com/",
  },
  {
    id: "zhipu",
    shortLabelZh: "智谱 AI",
    shortLabelEn: "Zhipu AI",
    labelZh: "智谱 AI（国内直连 · embedding-3）",
    labelEn: "Zhipu AI (embedding-3)",
    traitZh: "国内直连 · 中文科研术语表现友好",
    traitEn: "China direct · Strong CJK terminology support",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    model: "embedding-3",
    models: ["embedding-3", "embedding-2"],
    dimensionsHint: "2048",
    signupUrl: "https://open.bigmodel.cn/",
  },
  {
    id: "openai",
    shortLabelZh: "OpenAI 官方",
    shortLabelEn: "OpenAI",
    labelZh: "OpenAI 官方（需海外网络 · text-embedding-3-small）",
    labelEn: "OpenAI Official (text-embedding-3-small)",
    traitZh: "需海外网络与预充余额 · 英文学术表现极稳",
    traitEn: "Requires global network & prepaid billing · Gold standard",
    baseUrl: "https://api.openai.com/v1",
    model: "text-embedding-3-small",
    models: ["text-embedding-3-small", "text-embedding-3-large"],
    dimensionsHint: "1536",
    signupUrl: "https://platform.openai.com/api-keys",
  },
  {
    id: "ollama",
    shortLabelZh: "本地 Ollama",
    shortLabelEn: "Local Ollama",
    labelZh: "本地 Ollama（完全离线免费 · 无需密钥）",
    labelEn: "Local Ollama (100% Offline · Zero API key)",
    traitZh: "100% 离线免费 · 无需密钥 · 需本机运行 Ollama",
    traitEn: "100% offline & free · Zero key · Local Ollama required",
    baseUrl: "http://127.0.0.1:11434/v1",
    model: "bge-m3",
    models: ["bge-m3", "qwen3-embedding", "nomic-embed-text"],
    dimensionsHint: "1024",
  },
  {
    id: "custom",
    shortLabelZh: "自定义",
    shortLabelEn: "Custom",
    labelZh: "自定义 OpenAI 兼容端点（OneAPI / 中转 / 校内网关）",
    labelEn: "Custom OpenAI-compatible endpoint",
    traitZh: "支持 OneAPI / 公益中转 / 校内镜像（支持按需拉取模型）",
    traitEn: "OneAPI / proxy / institutional OpenAI-compatible gateway",
    baseUrl: "",
    model: "",
    models: [],
    dimensionsHint: "",
  },
];

export function matchEmbeddingPresetId(baseUrl: string, model: string): string {
  const b = String(baseUrl || "")
    .trim()
    .replace(/\/+$/, "")
    .toLowerCase();
  const m = String(model || "")
    .trim()
    .toLowerCase();
  if (!b && !m) return "siliconflow";
  if (
    !b &&
    (m === "text-embedding-3-small" || m === "text-embedding-3-large")
  ) {
    return "openai";
  }
  if (b.includes("api.siliconflow.")) return "siliconflow";
  if (b.includes("127.0.0.1:11434") || b.includes("localhost:11434"))
    return "ollama";
  for (const p of EMBEDDING_PRESETS) {
    if (p.id === "custom") continue;
    if (b && b === p.baseUrl.toLowerCase()) return p.id;
  }
  return "custom";
}

export interface PreviewCollectionItem {
  key: string;
  name: string;
  path: string;
  item_count: number;
  top_level?: boolean;
}

export function renderDomainModePreview(
  host: HTMLElement,
  opts: {
    domainMode: "per_collection" | "unified";
    collections: PreviewCollectionItem[];
    litDir: string;
    isZh: boolean;
  }
): void {
  host.empty?.();
  if (typeof host.empty !== "function") {
    host.textContent = "";
  }
  const wrap = host.createDiv({
    cls: "pf-domain-live-preview",
    attr: { "data-mode": opts.domainMode },
  });

  const litName = (opts.litDir || "Literature").trim() || "Literature";
  const topFolders =
    opts.collections.length > 0
      ? opts.collections
      : [
          {
            key: "DEMO1",
            name: opts.isZh ? "课题1-基础研究" : "Topic-A",
            path: "Topic-A",
            item_count: 42,
          },
          {
            key: "DEMO2",
            name: opts.isZh ? "课题2-临床随访" : "Topic-B",
            path: "Topic-B",
            item_count: 19,
          },
        ];

  // Left card: Folder tree in Obsidian Vault
  const leftCard = wrap.createDiv({ cls: "pf-preview-pane pf-fade-swap" });
  leftCard.createDiv({
    cls: "pf-preview-pane-title",
    text: opts.isZh ? "Obsidian 目录实时预览" : "Vault Folder Preview",
  });
  const tree = leftCard.createDiv({ cls: "pf-preview-tree" });
  const rootNode = tree.createDiv({ cls: "pf-preview-node is-root" });
  const rootIcon = rootNode.createEl("span", { cls: "pf-preview-node-icon" });
  setPfIcon(rootIcon, "folder", 13);
  rootNode.createEl("span", { text: ` ${litName}/` });

  if (opts.domainMode === "per_collection") {
    for (const col of topFolders.slice(0, 4)) {
      const folderLine = tree.createDiv({
        cls: "pf-preview-node is-branch pf-fade-item",
      });
      folderLine.createEl("span", { text: "├── " });
      const folderIcon = folderLine.createEl("span", {
        cls: "pf-preview-node-icon",
      });
      setPfIcon(folderIcon, "folder", 13);
      folderLine.createEl("span", { text: ` ${col.name}/ ` });
      folderLine.createEl("span", {
        cls: "pf-preview-count",
        text: opts.isZh ? `(${col.item_count} 篇)` : `(${col.item_count})`,
      });
    }
    if (topFolders.length > 4) {
      tree.createDiv({
        cls: "pf-preview-node is-branch is-more",
        text: opts.isZh
          ? `└── … 共 ${topFolders.length} 个课题目录`
          : `└── … ${topFolders.length} topic folders`,
      });
    }
  } else {
    const totalCount = topFolders.reduce(
      (acc, c) => acc + (c.item_count || 0),
      0
    );
    const flatLine = tree.createDiv({
      cls: "pf-preview-node is-branch pf-fade-item",
    });
    flatLine.createEl("span", { text: "├── " });
    const fileIcon = flatLine.createEl("span", {
      cls: "pf-preview-node-icon",
    });
    setPfIcon(fileIcon, "file-text", 13);
    flatLine.createEl("span", {
      text: opts.isZh
        ? " 所有文献统一平铺此目录 "
        : " All papers unified here ",
    });
    flatLine.createEl("span", {
      cls: "pf-preview-count",
      text: opts.isZh ? `(${totalCount} 篇)` : `(${totalCount})`,
    });
    tree.createDiv({
      cls: "pf-preview-node is-leaf pf-fade-item",
      text: opts.isZh
        ? "│     └─ 笔记内自动带 Zotero 分类标签"
        : "│     └─ Auto-tagged with Zotero collections",
    });
  }

  // Right card: Always ONE unified Base table with sticky filter bar
  const rightCard = wrap.createDiv({ cls: "pf-preview-pane pf-fade-swap" });
  rightCard.createDiv({
    cls: "pf-preview-pane-title",
    text: opts.isZh
      ? "单一 Base 总表（始终只有 1 张表）"
      : "Single Master Base View",
  });
  const baseSim = rightCard.createDiv({ cls: "pf-preview-base-sim" });
  const pills = baseSim.createDiv({ cls: "pf-preview-pills" });
  pills.createEl("span", {
    cls: "pf-preview-pill is-active",
    text: opts.isZh ? "全部" : "All",
  });
  for (const col of topFolders.slice(0, 3)) {
    pills.createEl("span", {
      cls: "pf-preview-pill pf-fade-item",
      text: col.name,
    });
  }
  const miniRows = baseSim.createDiv({ cls: "pf-preview-mini-rows" });
  for (const col of topFolders.slice(0, 3)) {
    const r = miniRows.createDiv({ cls: "pf-preview-mini-row" });
    r.createEl("span", { cls: "pf-preview-dot" });
    r.createEl("span", {
      cls: "pf-preview-row-title",
      text: opts.isZh ? `${col.name} 示例文献` : `${col.name} paper`,
    });
    r.createEl("span", {
      cls: "pf-preview-row-badge",
      text: opts.domainMode === "per_collection" ? col.name : col.path,
    });
  }
}
