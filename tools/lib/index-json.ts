// index.json: the list of blocks Omniscope reads to offer community blocks in the app.
// Same rules as the create_index.py it replaces, so the output is byte for byte the same.
import { join } from "node:path";
import { manifestDirs, readJson, cmp } from "./items.ts";
import { pythonJsonDump } from "./pyjson.ts";

export const SUPPORTED_OPTIONS_VERSIONS = [1];
// manifest key -> index key; a block without one of these is an error.
const REQUIRED: Record<string, string> = { name: "displayName", language: "language", optionsVersion: "optionsVersion" };
// Filled with a default when missing or null.
const DEFAULTS: Record<string, unknown> = { tags: [], category: "Custom scripts", description: "" };
// Copied only when present (even when null).
const OPTIONAL = ["subcategory", "icon"];

export interface IndexEntry {
  path: string;
  [key: string]: unknown;
}

export function indexEntry(path: string, manifest: Record<string, any>): IndexEntry | null {
  if (!("optionsVersion" in manifest) || !SUPPORTED_OPTIONS_VERSIONS.includes(manifest.optionsVersion)) return null;
  const entry: IndexEntry = { path };
  for (const [key, out] of Object.entries(REQUIRED)) {
    if (!(key in manifest) || manifest[key] === null) throw new Error(`Key ${key} is required but not present in manifest ${path}`);
    entry[out] = manifest[key];
  }
  for (const [key, def] of Object.entries(DEFAULTS)) {
    entry[key] = !(key in manifest) || manifest[key] === null ? def : manifest[key];
  }
  for (const key of OPTIONAL) if (key in manifest) entry[key] = manifest[key];
  return entry;
}

export function buildIndex(root: string): { blocks: IndexEntry[] } {
  const blocks: IndexEntry[] = [];
  for (const dir of manifestDirs(root)) {
    const e = indexEntry(dir, readJson(join(root, dir, "manifest.json")));
    if (e) blocks.push(e);
  }
  blocks.sort((a, b) => cmp(a.path, b.path));
  return { blocks };
}

export function indexText(root: string): string {
  return pythonJsonDump(buildIndex(root), 4);
}
