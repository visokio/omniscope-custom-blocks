import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { buildSite, lastUpdated } from "../site/build-site.ts";
import type { Item } from "../site/model.ts";
import { demoServerUrl } from "../site/model.ts";
import { CONFIG, loadItems } from "../repo.ts";

const FIX = join(import.meta.dirname, "fixtures", "blocks-tree");

test("gallery builds an index, a page per block and catalogue.json", () => {
  const out = mkdtempSync(join(tmpdir(), "site-"));
  const items = loadItems(FIX);
  const r = buildSite(CONFIG, items, FIX, out, "https://example.org/g/");
  assert.equal(r.pages, items.length + 1);
  const index = readFileSync(join(out, "index.html"), "utf8");
  assert.match(index, /class="chips"/);
  assert.match(index, /href="about.html"/);
  assert.match(index, /Blocks\+and\+Views\+Explorer/);
  assert.match(readFileSync(join(out, "about.html"), "utf8"), /The visokio-agents tag/);
  assert.match(index, /href="Preparation\/Conditional%20Execution\/index.html"/);
  assert.ok(existsSync(join(out, "Preparation", "Conditional Execution", "index.html")));
  assert.ok(existsSync(join(out, "assets", "style.css")));
  const cat = JSON.parse(readFileSync(join(out, "catalogue.json"), "utf8"));
  assert.equal(cat.kind, "blocks");
  assert.equal(cat.items.length, items.length);
  for (const k of ["id", "name", "category", "description", "tags", "inputs", "options", "links"]) assert.ok(k in cat.items[0], k);
  assert.equal(cat.items[0].links.page.startsWith("https://example.org/g/"), true);
});

test("demo server links are derived from the repository path", () => {
  assert.equal(demoServerUrl({ ...CONFIG, demoServerBase: "https://s/Community/Blocks" }, "Preparation/Join/Fuzzy-Join"),
    "https://s/Community/Blocks/Preparation/Join/Fuzzy-Join/demo.iox/");
});

test("lastUpdated dates an item from its folder's last commit, and gives nothing without a full history", () => {
  const dir = mkdtempSync(join(tmpdir(), "history-"));
  const git = (args: string[], date: string) => execFileSync("git", ["-C", dir, "-c", "user.name=t", "-c", "user.email=t@example.org", ...args],
    { env: { ...process.env, GIT_AUTHOR_DATE: date, GIT_COMMITTER_DATE: date }, stdio: "ignore" });
  const items = ["a", "b"].map((path) => ({ path })) as Item[];
  assert.equal(lastUpdated(dir, items).size, 0);
  git(["init", "-q"], "");
  for (const [path, date] of [["a", "2024-01-02T12:00:00Z"], ["b", "2025-03-04T12:00:00Z"]]) {
    mkdirSync(join(dir, path));
    writeFileSync(join(dir, path, "f"), path);
    git(["add", "."], date);
    git(["commit", "-qm", path], date);
  }
  assert.deepEqual([...lastUpdated(dir, items)], [["a", "2024-01-02"], ["b", "2025-03-04"]]);
  const shallow = mkdtempSync(join(tmpdir(), "shallow-"));
  execFileSync("git", ["clone", "-q", "--depth", "1", `file://${dir}`, shallow], { stdio: "ignore" });
  assert.equal(lastUpdated(shallow, items).size, 0);
});
