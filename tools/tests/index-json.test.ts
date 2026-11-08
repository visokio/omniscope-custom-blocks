import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { indexText, buildIndex, indexEntry } from "../lib/index-json.ts";
import { pythonJsonDump } from "../lib/pyjson.ts";
import { repoRoot } from "../lib/items.ts";

const FIX = join(import.meta.dirname, "fixtures");

test("golden: reproduces create_index.py byte for byte on a fixture tree", () => {
  // blocks-tree.expected-index.json was written by the create_index.py this tool replaced, run on blocks-tree/.
  // The fixture covers sub-manifests without optionsVersion, an old optionsVersion, a space in a path,
  // null tags, non-ASCII text (escaped as Python does), tabs and quotes.
  const expected = readFileSync(join(FIX, "blocks-tree.expected-index.json"), "utf8");
  assert.equal(indexText(join(FIX, "blocks-tree")), expected);
});

test("python json.dump format: escapes, nesting and numbers", () => {
  assert.equal(pythonJsonDump({ a: [], b: {}, c: [1, 0.5, null, true], d: "é 😀" }, 4),
    '{\n    "a": [],\n    "b": {},\n    "c": [\n        1,\n        0.5,\n        null,\n        true\n    ],\n    "d": "\\u00e9\\u2028\\ud83d\\ude00"\n}');
});

test("index skips the tools folder and language sub-manifests", () => {
  const paths = buildIndex(join(FIX, "blocks-tree")).blocks.map((b) => b.path);
  assert.ok(!paths.some((p) => p.endsWith("/R")), "the R sub-manifest has no optionsVersion and is not listed");
  assert.ok(!paths.includes("Inputs/Old"), "optionsVersion 0 is not listed");
  const repoPaths = buildIndex(repoRoot()).blocks.map((b) => b.path);
  assert.ok(!repoPaths.some((p) => p.startsWith("tools/")), "fixtures under tools/ never reach index.json");
});

test("index.json in the repository is up to date (run npm run build)", () => {
  const root = repoRoot();
  assert.equal(readFileSync(join(root, "index.json"), "utf8"), indexText(root));
});

test("a missing required key is an error", () => {
  assert.throws(() => indexEntry("X", { optionsVersion: 1, language: "R" }), /Key name is required/);
});
