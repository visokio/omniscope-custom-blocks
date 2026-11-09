// The blocks repository's side of the shared tools: its configuration and how a block becomes a gallery item.
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { manifestDirs, readJson } from "./lib/items.ts";
import { indexEntry } from "./lib/index-json.ts";
import { type Item, type ItemOption, type RepoConfig, AI_BUILT_TAG } from "./site/model.ts";

export const CONFIG: RepoConfig = {
  kind: "blocks",
  title: "Omniscope Custom Blocks",
  intro: "Python and R blocks that add analytics, data preparation, connectors and outputs to Omniscope workflows. Each page shows what the block does, its options, and how to try it.",
  githubRepo: "visokio/omniscope-custom-blocks",
  branch: process.env.GALLERY_BRANCH || "master",
  demoServerBase: process.env.DEMO_SERVER_BASE ?? "https://public.omniscope.me/Community/Blocks",
  demoProject: "demo.iox",
  noun: ["block", "blocks"],
  otherGallery: {
    title: "Omniscope Custom Views", url: process.env.OTHER_GALLERY_URL ?? "https://visokio.github.io/omniscope-custom-views/", noun: ["view", "views"],
  },
  // The colours Omniscope's block picker draws behind each category's icons (read from the app, Nov 2026).
  tileColours: {
    Inputs: "rgb(237,169,71)", Connectors: "rgb(207,128,89)", Preparation: "rgb(120,67,136)",
    Analytics: "rgb(106,193,212)", Outputs: "rgb(147,196,76)", "Code & AI": "rgb(91,91,91)",
  },
  categoryOrder: ["Inputs", "Connectors", "Preparation", "Analytics", "Outputs", "Code & AI"],
};

/** Base URL the gallery is published at (GitHub Pages). */
export const SITE_URL = process.env.SITE_URL ?? "https://visokio.github.io/omniscope-custom-blocks/";

const TYPE_NAMES: Record<string, string> = {
  Field: "Field", Fields: "Fields", Text: "Text", Boolean: "Yes / no", Choice: "Choice", Integer: "Whole number",
  Double: "Number", Password: "Password", File: "File",
};

function optionType(o: any): string {
  const t = String(o["@visokiotype"] ?? "").replace(/^CustomBlockSchema\./, "").replace(/CustomBlockPublicOption$/, "");
  return TYPE_NAMES[t] ?? t;
}

/** Blocks the app lists: every manifest that index.json includes. Sub-manifests (language variants) are left out. */
export function loadItems(root: string): Item[] {
  const items: Item[] = [];
  for (const path of manifestDirs(root)) {
    const m = readJson(join(root, path, "manifest.json"));
    if (!indexEntry(path, m)) continue;
    const opts: any[] = Array.isArray(m.options) ? m.options : [];
    const toOpt = (o: any): ItemOption => ({ name: o.name, title: o.title ?? o.name, type: optionType(o), description: o.description ?? undefined });
    const isField = (o: any) => /\.Fields?CustomBlockPublicOption$/.test(o["@visokiotype"] ?? "");
    const files = readdirSync(join(root, path));
    const sample = existsSync(join(root, path, "sample-data"))
      ? readdirSync(join(root, path, "sample-data")).filter((f) => /\.(csv|tsv|txt|json|xlsx)$/i.test(f)).sort().map((f) => "sample-data/" + f)
      : [];
    const tags: string[] = Array.isArray(m.tags) ? m.tags : [];
    items.push({
      path,
      name: m.name,
      category: m.category ?? "Custom scripts",
      categories: [m.category ?? "Custom scripts"],
      icon: typeof m.icon === "string" && m.icon.startsWith("data:") ? { dataUri: m.icon } : undefined,
      subcategory: m.subcategory ?? null,
      description: m.description ?? "",
      tags,
      aiBuilt: tags.includes(AI_BUILT_TAG),
      language: m.language,
      inputs: opts.filter(isField).map(toOpt),
      options: opts.filter((o) => !isField(o)).map(toOpt),
      outputs: (Array.isArray(m.blockOutputs) ? m.blockOutputs : []).map((o: any) => ({ id: o.id, label: o.label ?? o.id, description: o.tooltip ?? o.displayName ?? undefined })),
      thumbnail: files.includes("thumbnail.png") ? "thumbnail.png" : undefined,
      showcase: existsSync(join(root, path, "showcase", "showcase.md")) ? "showcase/showcase.md" : undefined,
      readme: files.includes("README.md") ? "README.md" : undefined,
      sampleData: sample,
      hasDemo: files.includes("demo.ioz"),
      libraries: [],
    });
  }
  return items;
}
