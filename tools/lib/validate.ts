// Manifest checks for blocks. Errors fail the build; warnings are reported (older blocks predate some rules).
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { manifestDirs, readJson } from "./items.ts";
import { indexEntry } from "./index-json.ts";

export interface Problem { path: string; level: "error" | "warning"; message: string }

export const CATEGORIES = ["Analytics", "Connectors", "Code & AI", "Custom scripts", "Inputs", "Outputs", "Preparation"];
const FILE_SET = ["manifest.json", "README.md", "icon.svg", "thumbnail.png", "sample-data", "showcase", "tests", "demo.ioz"];

export function validateBlock(root: string, path: string, m: any): Problem[] {
  const out: Problem[] = [];
  const err = (message: string) => out.push({ path, level: "error", message });
  const warn = (message: string) => out.push({ path, level: "warning", message });
  for (const k of ["name", "language", "optionsVersion"]) if (m[k] === undefined || m[k] === null) err(`missing "${k}"`);
  if (m.language && !["PYTHON", "R"].includes(m.language)) err(`language must be PYTHON or R, not ${m.language}`);
  if (m.scriptFilename && !existsSync(join(root, path, m.scriptFilename))) err(`script file ${m.scriptFilename} not found`);
  if (m.category && !CATEGORIES.includes(m.category)) warn(`category "${m.category}" is not one of ${CATEGORIES.join(", ")}`);
  if (m.tags !== undefined && m.tags !== null && (!Array.isArray(m.tags) || m.tags.some((t: unknown) => typeof t !== "string"))) err("tags must be a list of text");
  const names = new Set<string>();
  for (const o of Array.isArray(m.options) ? m.options : []) {
    if (!o.name) { err("an option has no name"); continue; }
    if (names.has(o.name)) err(`option "${o.name}" appears twice`);
    names.add(o.name);
    if (!o.title) warn(`option "${o.name}" has no title`);
    if (/\.Fields?CustomBlockPublicOption$/.test(o["@visokiotype"] ?? "") && o.width === "HALF")
      warn(`field picker "${o.name}" is HALF width: field names get cut off; use ONE`);
  }
  const ids = new Set<string>();
  for (const o of Array.isArray(m.blockOutputs) ? m.blockOutputs : []) {
    if (ids.has(o.id)) err(`output id "${o.id}" appears twice`);
    ids.add(o.id);
    if (/^\s*\d*\s*$/.test(String(o.label ?? ""))) warn(`output "${o.id}" is labelled "${o.label ?? ""}": the workflow canvas shows the label, so give it a word or two`);
  }
  if (Array.isArray(m.tags) && m.tags.includes("visokio-agents")) {
    const files = readdirSync(join(root, path));
    for (const f of FILE_SET) if (!files.includes(f)) err(`visokio-agents block is missing ${f}`);
  }
  return out;
}

export function validateRepo(root: string): Problem[] {
  const out: Problem[] = [];
  for (const path of manifestDirs(root)) {
    let m: any;
    try { m = readJson(join(root, path, "manifest.json")); } catch (e) { out.push({ path, level: "error", message: (e as Error).message }); continue; }
    if (!indexEntry(path, m)) continue; // language variants and old manifests: not listed, not checked
    out.push(...validateBlock(root, path, m));
  }
  return out;
}
