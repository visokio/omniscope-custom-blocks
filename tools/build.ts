// npm run build: regenerate index.json, check every manifest, and build the gallery into _site/.
//   npm run build -- --check      fail if index.json is out of date (CI on branches), build nothing
//   npm run build -- --no-site    index.json and checks only
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./lib/items.ts";
import { indexText } from "./lib/index-json.ts";
import { validateRepo } from "./lib/validate.ts";
import { buildSite } from "./site/build-site.ts";
import { parseRelated, readRelated } from "./site/related.ts";
import { CONFIG, SITE_URL, loadItems } from "./repo.ts";

const root = repoRoot();
const args = process.argv.slice(2);
const indexFile = join(root, "index.json");
const fresh = indexText(root);
const current = existsSync(indexFile) ? readFileSync(indexFile, "utf8") : "";

const problems = validateRepo(root);
// related.json: every link must lead somewhere, and links between two items here go both ways.
for (const p of parseRelated(CONFIG, readRelated(root), loadItems(root)).problems) problems.push({ ...p, level: "error" });
for (const p of problems.filter((p) => p.level === "error")) console.error(`error   ${p.path}: ${p.message}`);
const warnings = problems.filter((p) => p.level === "warning");
if (warnings.length) console.log(`${warnings.length} warnings (run with --warnings to list them)`);
if (args.includes("--warnings")) for (const p of warnings) console.log(`warning ${p.path}: ${p.message}`);
if (problems.some((p) => p.level === "error")) process.exit(1);

if (args.includes("--check")) {
  if (fresh !== current) { console.error("index.json is out of date: run npm run build and commit it"); process.exit(1); }
  console.log("index.json is up to date");
  process.exit(0);
}
if (fresh !== current) { writeFileSync(indexFile, fresh); console.log("index.json regenerated"); }
else console.log("index.json unchanged");

if (!args.includes("--no-site")) {
  const r = buildSite(CONFIG, loadItems(root), root, join(root, "_site"), SITE_URL);
  console.log(`gallery: ${r.pages} pages, ${r.files} files copied, in ${r.outDir}`);
}
