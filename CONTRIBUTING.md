# Maintaining the custom blocks

How to add a block to this repository, or refresh one, without missing a step. It is written for people and for
coding agents alike. The [README](README.md) says what the repository is; this file says how it works.

## What a block folder holds

Blocks sit in category folders (`Analytics/`, `Connectors/`, `Inputs/`, `Outputs/`, `Preparation/` and so on),
optionally in a subfolder such as `Preparation/Join/`. Add a new category folder only when no existing one fits.

| File | What it is | Needed |
|---|---|---|
| `manifest.json` | The block definition Omniscope reads: name, options, outputs, icon, description | Always |
| `script.py` or `script.R` | The code (the manifest's `scriptFilename`) | Always |
| `README.md` | What the block does, its options and outputs; GitHub and the gallery show it | Always |
| `icon.svg`, `thumbnail.png` | The icon's source and a picture of the block tile (for GitHub and the gallery card) | Recommended |
| `sample-data/` | Invented sample data (CSV) used by the tests, the demo and the gallery's download link | New blocks |
| `showcase/showcase.md` | The gallery page: the problem it solves, what goes in and out, how to try it; images beside it | New blocks |
| `tests/` | Unit tests (`tests/test_block.py` for Python blocks) | New blocks |
| `demo.ioz` | A demo and test project: sample data, the block, and a check of its output | New blocks |

`npm run build` checks the rules below and fails on an error. Blocks tagged `visokio-agents` must have the whole set.

### Manifest rules

- **Export it from Omniscope.** Design the block in the block editor and export it (the editor's export button
  gives a ZIP with the manifest and script). Hand edits are fine for text, but keep the key order Omniscope writes.
- **`optionsVersion` 1.** Only manifests with `optionsVersion: 1` are listed in `index.json`. One block per
  folder: no language-variant sub-folders (old ones were removed in 2026).
- **`category` and `subcategory`** decide where the block appears in Omniscope's block picker. Use an existing
  category; reuse an existing subcategory's spelling and capitalisation.
- **`tags`**: lower-case search words. Blocks built by Visokio's agents carry `visokio-agents`, which also
  shows as a badge in the gallery.
- **Icon.** Omniscope draws each block as a tile in its category's colour and puts the manifest's `icon` on it,
  in the tile's inner 28 x 28 area. So the icon is the glyph alone: white (optionally with a second, half-transparent
  white tone), on a transparent background, with no tile, frame or text of its own, like the core blocks' icons.
  Keep its source as `icon.svg` (viewBox 0 0 28 28) and put a 112 x 112 PNG of it in the manifest as a
  `data:image/png;base64,...` URI.
  A block for a named service or product uses that brand's own logo recoloured white, never a redrawn imitation:
  see "Brand logos as icons" below.
- **`description`** is one or two sentences (the picker and the gallery card show it). **`introductoryText`** is
  Markdown shown when the block is added to a workflow: what it does and how to set it up.
- **Output labels.** Each entry in `blockOutputs` has three texts. `label` is what the workflow canvas draws beside
  the output connector: make it a short word or two ("Matched", "Summary"), never "1" or "2". `displayName` is
  only the hover text, and `id` is what the script writes to (`write_output(df, "matched")`). They are easy to
  confuse; the canvas shows `label`.
- **Option widths.** Field and Fields pickers should be `ONE` (full width): at `HALF` the field names are cut off.
  Use `HALF` only to put two small options (numbers, yes/no) side by side.
- **Option names** (`name`) are what the script reads with `get_option("name")`. A block added to a project is a
  copy, so changing the repository never changes projects that already use it; but keep an option's name while
  the option means the same thing, so people re-adding the block find their settings where they expect.
- **Dependencies.** Prefer what Omniscope's Python environment already has (pandas, numpy). Anything else goes in
  the manifest's `dependencies` field as pip specifications; Omniscope installs them on first run.

### Brand logos as icons

A connector, input or output for a named service (Trello, Jira, OpenAI, BigQuery, ...) shows that service's logo,
so people recognise it in the picker. Take the real logo (the brand's own one-colour version if it publishes one,
otherwise its full-colour logo or the block's previous icon) and replace its colours with white, keeping every
shape. Don't redraw it: hand-drawn imitations of logos come out inaccurate. How each kind of logo comes out right:

| The logo | Do this | Examples |
|---|---|---|
| A coloured shape on a transparent background | Turn every visible pixel white | HubSpot, OpenAI, DeepSeek |
| A white logo on a coloured square | Keep the light pixels as white, drop the square | Yahoo, Flipside |
| A shape with the logo cut into it | Make the shape white and the logo inside transparent | Trello, BigQuery |
| A logo on a white tile | Keep the dark pixels as white, drop the tile | MongoDB, SharePoint, Telegram |
| Detail shown only by two colours | Map the colours to two whites, one about half transparent | Jira, Dune, PowerPoint |

Then crop to the logo, centre it on a square transparent canvas and check it on the category's tile colour at
the picker's size: specks left from a plate's edge, or a plate's faint outline, show up there. A few lines of
Python with Pillow do it, for example for "keep the light pixels":

```python
from PIL import Image
import numpy as np
im = np.asarray(Image.open("logo.png").convert("RGBA")).astype(float) / 255
lum = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
keep = np.clip((lum - 0.55) / 0.3, 0, 1)            # light pixels in, dark plate out
out = np.ones_like(im); out[..., 3] = im[..., 3] * keep
img = Image.fromarray((out * 255).astype("uint8"))
img = img.crop(img.getchannel("A").getbbox())        # then centre on a square canvas
```

A logo usually comes as a picture rather than a drawing, so `icon.svg` may hold it as an embedded PNG
(`<image width="28" height="28" href="data:image/png;base64,..."/>` in a 0 0 28 28 viewBox); make that PNG at
least 224 x 224 so the 112 x 112 manifest icon stays sharp.

## Tests

```bash
npm install
pip install -r tools/python/requirements.txt
npm test
```

`npm test` runs:

- **The tool tests** (`tools/tests/`, Node's test runner): `index.json` generation, including a golden test
  that proves the output is byte for byte what the original Python script produced; manifest checks; the gallery.
- **Every Python block's tests** (pytest, `tests/test_block.py` in each block). They run `script.py` against a
  stand-in for Omniscope's Python API (`tools/python/harness/`), which mimics what a block sees on a real
  server: integer fields as nullable `Int64`, text as `str`, time-zone-aware dates, a missing second input
  as `None`, options defaulted from the manifest, and an error for an option the manifest doesn't declare.

  ```python
  from harness.runner import run_block
  res = run_block(BLOCK_DIR, [df], {"item_field": "SKU"}).raise_for_error()
  res.output(0)   # the first output as a DataFrame; res.status, res.messages, res.error
  ```

  Cover normal data, empty input, wrong field types and a large input. Run one block's tests with
  `python3 -m pytest Analytics/ABC-Classification`.
- **R blocks** have a stand-in for Omniscope's R API in `tools/r/`: write testthat tests in `tests/test_block.R`
  and run them with `Rscript tools/r/run-tests.R <block folder>` (needs R and testthat). They are not yet part of
  `npm test` or the Actions.

## Testing on your own Omniscope server

Every new block has a `demo.ioz`: the sample data in a File block, the block, and a Validate Data (or Compare)
block that checks the output against an expected result. It is for trying the block by hand, by people or
agents; nothing runs it automatically.

1. In Omniscope, open a folder you can write to, press **+** > **Upload** and choose `demo.ioz`; then click
   `demo.ioz` in the file list and press **Import project**. It becomes the project `demo.iox` (an existing
   `demo.iox` is not replaced: delete or rename it first).
2. Run the workflow. The block's outputs appear on the canvas; the check block passes if the output is as
   expected.
3. To test a change, edit the block in the project (the block editor shows the script) or replace it with the
   new version, and run again.

When you change a block, export the demo project again.

**Exporting a demo project.** In the project, open the menu (⋮) and choose **Download IOZ file**. Keep
**Include Report data** ticked, untick **Include project history** (it records every edit, including ones you
wouldn't publish) and leave **Include passwords** unticked. Then run `npm run slim-ioz -- path/to/demo.ioz`: it
removes the server's branding (about 1 MB of fonts and logos the importing server doesn't use). Commit the result
as the item's `demo.ioz`; keep it under 1 MB.

## Building

```bash
npm run build       # regenerates index.json, checks every manifest, builds the gallery into _site/
npm run serve       # serves _site/ on http://localhost:8081/ (views use 8080)
```

- **`index.json`** is the list Omniscope reads to offer the blocks in the app. It is generated from the
  manifests; never edit it by hand. Commit it with the manifest change.
- **The gallery** (`_site/`, not committed) has a page per block built from its manifest and
  `showcase/showcase.md` (or `README.md` for blocks without a showcase), an index page with search and filters,
  and `catalogue.json`, a machine-readable list for agents.
- `npm run build -- --warnings` lists the softer problems (numeric output labels, half-width field pickers) that
  older blocks still have.

### Related blocks and views (`related.json`)

Each gallery page has a **Related** section, from `related.json`: the core blocks and views, community blocks here
and community views in [omniscope-custom-views](https://github.com/visokio/omniscope-custom-views) that a user
should know about next to this block.

```json
{
  "items": {
    "<block path>": {
      "summary": "How this block fits with its neighbours: what to use instead for what, and why this one exists.",
      "overlaps": [{ "coreBlock": "<name as in the picker>", "note": "How they differ, and when to use which." }],
      "seeAlso": [{ "block": "<path of a block here>", "note": "..." }, { "view": "<path in omniscope-custom-views>", "name": "<its name>", "note": "..." }]
    }
  }
}
```

- **summary** (shown first): one to three sentences on the overall picture, not a repeat of the notes. Use
  `**bold**` for names. Every item with related items should have one.
- A reference is one of `coreBlock`, `coreView` (the picker's name), `block` or `view` (a community item's path).
  A reference to the other repository also gives the item's `name`, since this repository can't read its manifest.
- **overlaps**: the other item does much the same job, so a user could pick either. The note says how they
  differ and when to use which. **seeAlso**: a partial alternative, or something that works with it (a block whose
  output a view shows). Be selective: most items have none to three.
- **Links go both ways.** When one block here lists another, the other lists it back (in `overlaps` if it's an
  overlap); `npm run build` fails otherwise, and when a path doesn't exist. A link to a view in
  omniscope-custom-views should be mirrored there too, in the same change if you can.
- When you add a block, check the core picker and both galleries for anything similar, and add its entries.

## What the GitHub Actions do

- **Checks** (every push, and pull requests from forks): rebuilds `index.json`, checks the manifests, type-checks the tools
  and runs `npm test`. On `master`, if `index.json` was out of date (typically after a manifest edit in
  GitHub's web editor) it commits the regenerated file as "Regenerate index.json after <commit>". On other
  branches an out-of-date `index.json` fails the check instead. The badge in the README shows the result.
- **Pages** (every push to `master`): builds the gallery and publishes it with GitHub Pages. There is no staging
  site: whatever reaches `master` goes live, so preview with `npm run build && npm run serve` first.
  (Settings > Pages > Source must be "GitHub Actions".)
- **Demo links** (manual, from the Actions tab): checks that every block with a `demo.ioz` has its demo project on
  the public demo server, and lists the missing ones. It changes nothing.

## When the app sees a change

Omniscope fetches `index.json` and the block files through the jsDelivr CDN, which caches GitHub content. A
change on `master` can take up to a day to reach the app. To make it visible sooner, purge the cached copies of
the files you changed, for example:

```
https://purge.jsdelivr.net/gh/visokio/omniscope-custom-blocks@master/index.json
https://purge.jsdelivr.net/gh/visokio/omniscope-custom-blocks@master/Preparation/Join/As-Of-Join/script.py
```

Adding a block to a workflow copies it into the project, so a change here never alters a project that already
uses the block. To pick up a new version, replace the block in the workflow with a fresh one from the block
picker.

## The public demo server

Each block's demo project is also on `https://public.omniscope.me/Community/Blocks/`, at the same path as in this
repository (for example `.../Community/Blocks/Analytics/ABC-Classification/demo.iox/`). Gallery pages link to it.
Each folder there has a `README.md` that links back to the gallery.

```bash
npm run bundle:demo-server                      # writes _bundle/tree/ and a zip of it
OMNI_URL=https://public.omniscope.me OMNI_USER=... OMNI_PASS=... npm run publish:demo-server
# after failures, add -- --missing-only to do only what is still missing
```

`publish:demo-server` drives the Omniscope web UI in headless Chrome: it uploads each `demo.ioz` and README,
opens the `.ioz` (which unpacks it into `demo.iox`), waits for the project, and deletes the `.ioz`. It needs an
account that can write to the folder. The **Demo links** workflow then confirms every link works.

Then **run each demo once**. Unpacking doesn't run the workflow, and visitors can only view, so until it has run
its blocks show as never run. Use the Workflow REST API (the account needs "Workflow Execution via APIs"): POST
`{"blocks": ["<the demo's check block>"]}` to `<project>/w/execute`, then GET `<project>/w/job/<jobId>/state`
until it says `COMPLETED`. The server stores new folder names capitalised (`JSON` becomes `Json`) and redirects
other spellings, but a POST doesn't follow the redirect: GET the project's address first and POST to the address
it redirects to.

## Adding or refreshing a block with a coding agent

An agent session can do the whole job. Give it this file and the block's folder, and ask for:

1. The block's code and manifest, following the manifest rules above, with invented sample data in
   `sample-data/` (say in the README that it's invented).
2. `tests/test_block.py` with the harness, passing under `npm test`.
3. `README.md` (options and outputs tables generated from the manifest are a good start), and
   `showcase/showcase.md` in the shape of the existing ones: the problem it solves, what goes in, the options,
   what comes out, where it pays off, how it fits into a workflow, and "Try it". How it relates to other
   blocks goes in `related.json`, not the showcase: the gallery shows it under Related.
4. A demo project on a test server: sample data, the block, a Validate Data check; export it as `demo.ioz`.
5. `npm run build` and `npm test` clean, and the gallery page checked with `npm run serve`.

Ask it to check, before building, which core Omniscope block or existing community block comes closest, and to
say in the showcase why you'd use this one instead.
(The `visokio-agents` tag is only for blocks built by Visokio's own agents.)

The blocks tagged `visokio-agents` in this repository were built that way, by Visokio's agents working to Visokio's
instructions, and tested with the harness here and on a real Omniscope server.

## Standards every block meets

Agreed with Visokio for the 2026 refresh; keep new and updated blocks to them.

- **README sections**: what it does, options and outputs, a **"Why do this in Omniscope"** section that is
  specific to this block (what you get from doing it in a workflow rather than by hand or elsewhere: the
  particular steps it removes, what it combines with, what you'd change in its script), no boilerplate repeated
  across blocks; libraries and licences; and how it relates to the nearest core or community block (also listed in `related.json`).
- **Icon**: one white glyph (optionally a second, half-transparent white tone) on a transparent background, see
  the manifest rules. No tile, frame or colour: the app draws the tile. A brand's logo is recoloured, not redrawn.
- **Streaming blocks stay streaming.** A block with `apiMode` `STREAM_TRANSFORM` was written so its input isn't
  limited by Python's or R's memory. Don't switch it to `BATCH` to make it easier to fix, test or demo; design
  the fix within streaming (a rules text option instead of a second input, types fixed from the first chunk),
  or agree the change with the block's owner.
- **Breaking changes are allowed.** An item added to a project is a copy, so changing it here never changes
  projects that use it. Fix things properly rather than preserving a fault, but keep an option's key while the
  option means the same thing, and list every behaviour change under "Breaking changes" in the change notes or
  pull request, so a reviewer can judge them.
- **Licence.** The repository is MIT-licensed (`LICENSE`); a contribution is accepted under the same licence.
- **Third-party code is loaded, not copied in.** Load libraries from a CDN at a pinned version (jsDelivr's
  `npm/` or `gh/<owner>/<repo>@<commit>/`), never commit a copy. Nothing under a copyleft licence (GPL, AGPL)
  goes into the repository. Name each library, its version and licence in the README's libraries section, with
  any terms that fall on whoever uses the item (a paid licence for business use, a service's terms).
- **Data is invented.** Sample data and demos use invented records (say so in the README), or Omniscope's built-in
  Demo data datasets, which are fictional too. No real people, customers or transactions. Outlines and reference
  data from open sources carry their attribution in the README.
- **Demos that can't run say so on the canvas.** When a demo can't run the item for real (it needs an account,
  credentials, a server file, or permissions an anonymous viewer lacks), the workflow carries a note shape
  beside the item saying what isn't run and how to test it with your own setup.
- **Test it on a real server before it's done**, and after a merge add it from the app's own picker in a new
  project (the app reads the list from `master`, so that's the first time the picker route can be checked).

## Lessons for contributors

Things that have caught people (and agents) out:

- **pandas 2 and 3 alike.** Omniscope's Docker image and a server's own Python can carry different pandas
  versions. Text may arrive as the `str` dtype (pandas 3) or `object` (pandas 2): test with
  `pd.api.types.is_string_dtype`, not `select_dtypes(include="object")`. Never output dtype names.
- **Integer fields arrive as nullable `Int64`**, so a division can give `pd.NA` and break `float()`. Cast numeric
  inputs with `.astype("float64")` before arithmetic.
- **Dates are time-zone aware** (`datetime64[..., UTC]`). Strip the zone at the start (`tz_localize(None)`), work
  naive, and put it back on output; mixing aware and naive values raises "Mixed timezones detected".
- **Integer-labelled Series**: `s[a:b]` slices by position, not label. Use `.iloc` or `.loc` explicitly.
- **Weeks**: `to_period("W-MON")` means weeks *ending* on Monday. Weeks starting on Monday are `"W-SUN"`.
- **Ties**: round derived sort keys (for example to 6 decimal places) so floating-point noise never decides an
  order, and break ties explicitly.
- **Text placeholders**: values such as "N/A", "NA", "null" and "#N/A" can reach a Python block as missing
  values rather than text. A block that validates text should allow for both.
- **Leading spaces in output text are trimmed.** For indented labels use a visible mark ("· · Leeds") and a
  numeric level field.
- **Empty text and missing are the same** once a value has been through Omniscope.
- **Unset options**: treat `""` and `None` alike for optional Field options (`if not value:`).
- **`get_option()`** is case-insensitive and raises `KeyError` for an option the manifest doesn't declare.
- **`abort()`** ends the script at once; `cancel()` doesn't.
- **Second inputs** aren't declared in the manifest: read them with `read_input_records(input_number=1)`, which
  returns `None` when nothing is connected. Outputs are declared, in `blockOutputs`.
- **Performance**: build sets and dictionaries once, outside loops; cast integer matrices to float before large
  products (numpy's integer matrix product doesn't use BLAS).
- **Sample data headers**: avoid ALL-CAPS field names; Omniscope's File block can change their case on import.
