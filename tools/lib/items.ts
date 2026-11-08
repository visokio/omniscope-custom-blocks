// Finding the blocks in the repository: every folder with a manifest.json, outside the tooling.
import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

// Folders that never hold blocks. tools/ has test fixtures with manifests of their own.
export const SKIP_DIRS = new Set([".git", ".github", "node_modules", "tools", "_site", "_bundle", "__pycache__", ".pytest_cache"]);

export function repoRoot(): string {
  return fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]$/, "");
}

/** Repo-relative paths (with "/") of every folder holding a manifest.json, sorted. */
export function manifestDirs(root: string): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const name of readdirSync(dir)) {
      if (SKIP_DIRS.has(name) || name.startsWith(".")) continue;
      const p = join(dir, name);
      if (!statSync(p).isDirectory()) continue;
      if (existsSync(join(p, "manifest.json"))) out.push(relative(root, p).split(sep).join("/"));
      walk(p);
    }
  };
  walk(root);
  return out.sort(cmp);
}

/** Code-point order, as Python sorts strings (not localeCompare). */
export function cmp(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function readJson<T = any>(file: string): T {
  const text = readFileSync(file, "utf8");
  try {
    return JSON.parse(text.replace(/^﻿/, ""));
  } catch (e) {
    throw new Error(`JSON error in ${file}: ${(e as Error).message}`);
  }
}
