import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { validateBlock, validateRepo } from "../lib/validate.ts";
import { repoRoot } from "../lib/items.ts";

function block(files: Record<string, string> = {}) {
  const root = mkdtempSync(join(tmpdir(), "val-"));
  mkdirSync(join(root, "B"));
  for (const [f, c] of Object.entries(files)) writeFileSync(join(root, "B", f), c);
  return root;
}

test("every block manifest in the repository passes (errors only)", () => {
  const errors = validateRepo(repoRoot()).filter((p) => p.level === "error");
  assert.deepEqual(errors, []);
});

test("duplicate options and outputs, and a missing script, are errors", () => {
  const root = block();
  const probs = validateBlock(root, "B", {
    name: "B", language: "PYTHON", optionsVersion: 1, scriptFilename: "script.py",
    options: [{ name: "a", title: "A" }, { name: "a", title: "A" }],
    blockOutputs: [{ id: "o", label: "Out" }, { id: "o", label: "Out" }],
  });
  const msgs = probs.filter((p) => p.level === "error").map((p) => p.message);
  assert.ok(msgs.some((m) => /script file/.test(m)));
  assert.ok(msgs.some((m) => /option "a" appears twice/.test(m)));
  assert.ok(msgs.some((m) => /output id "o" appears twice/.test(m)));
});

test("numeric output labels and half-width field pickers are warnings", () => {
  const root = block({ "script.py": "" });
  const probs = validateBlock(root, "B", {
    name: "B", language: "PYTHON", optionsVersion: 1, scriptFilename: "script.py",
    options: [{ name: "f", title: "F", width: "HALF", "@visokiotype": "CustomBlockSchema.FieldCustomBlockPublicOption" }],
    blockOutputs: [{ id: "o", label: "1" }],
  });
  assert.equal(probs.filter((p) => p.level === "error").length, 0);
  assert.equal(probs.filter((p) => p.level === "warning").length, 2);
});

test("an visokio-agents block must have the full file set", () => {
  const root = block({ "script.py": "", "manifest.json": "{}" });
  const probs = validateBlock(root, "B", { name: "B", language: "PYTHON", optionsVersion: 1, tags: ["visokio-agents"] });
  assert.ok(probs.some((p) => p.level === "error" && /missing README.md/.test(p.message)));
});
