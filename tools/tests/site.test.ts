import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { buildSite } from "../site/build-site.ts";
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
