# Omniscope Custom Blocks

**[Browse the gallery](https://visokio.github.io/omniscope-custom-blocks/)**: every block with what it does, its
options, sample data and a demo project.

Community views (charts and other views for reports) are in [omniscope-custom-views](https://github.com/visokio/omniscope-custom-views)
([gallery](https://visokio.github.io/omniscope-custom-views/)).

To compare community and core blocks and views in one list, with filters, use the [Blocks and Views Explorer](https://public.omniscope.me/Community/Blocks+and+Views+Explorer.iox/r/Report/).

[![Checks](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/checks.yml/badge.svg)](https://github.com/visokio/omniscope-custom-blocks/actions/workflows/checks.yml)

Community blocks for [Omniscope](https://visokio.com/) workflows, written in Python or R: analytics, data
preparation, connectors, inputs and outputs. Omniscope lists them in its block picker, from this repository's
`index.json`.

## How Omniscope uses this repository

- Omniscope reads `index.json` to show the blocks in the block picker, grouped by category.
- Adding a block to a workflow **copies** it into the project. Editing or deleting a block here never changes a
  project that already uses it; to pick up a newer version, replace the block in the workflow with a fresh one
  from the picker.
- Each block's folder holds its `manifest.json` and script, a README and, for newer blocks, sample data, tests
  and a `demo.ioz` project you can import into your own Omniscope.

[Python and R API documentation](https://help.visokio.com/support/solutions/articles/42000071109-custom-block-r-python-api-reference)

## Built by Visokio's agents

Blocks tagged **visokio-agents** are community examples built by Visokio's agents, to extend Omniscope's core
blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on
Omniscope. They are tested by automated tests and were run on a real Omniscope server. They were not reviewed by
Omniscope's core team, so they are not on a par with the core blocks, which have years of manual, functional and
unit tests behind them. Their sample data is invented.

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) has everything needed to add or refresh a block: the file set and manifest
rules, the tests, the build, the gallery and the demo server. Fork the repository, add your block, run
`npm run build` and `npm test`, and open a pull request. Or export your block from Omniscope as a ZIP and send it
to support@visokio.com.

## Licence

MIT, see [LICENSE](LICENSE). Libraries that a block loads (named in its README) keep their own licences and terms.
