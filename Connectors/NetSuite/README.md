# NetSuite Connector

Reads a saved search or a SuiteQL query into an Omniscope workflow using NetSuite REST web services.
Authentication uses OAuth 2.0 client credentials with a certificate and a matching RSA private key.
Version 0.1.0 is for evaluation: **no live NetSuite account has been tested; production readiness is not established**.

## Inputs

None. The block reads from NetSuite; the generic input socket does not need a connection.

## NetSuite setup

Follow the [customer setup guide](customer-setup.md) to configure the integration application, restricted role,
certificate mapping and execution environment. Start with a small known source in Sample mode.
Saved-search REST requires the September NetSuite 2026.2 feature or later; confirm account availability.
SuiteQL queries must be prepared for your account and role. No paid third-party driver is used.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| SuiteTalk service URL | `service_url` | Text | Copy the HTTPS SuiteTalk origin from NetSuite Company Information > Company URLs. |
| Application client ID | `client_id` | Text | Client ID of the OAuth 2.0 integration application. |
| Certificate ID | `certificate_id` | Text | Certificate ID from the OAuth 2.0 Client Credentials (M2M) mapping. |
| Private-key file | `private_key_file` | File | Matching PEM RSA private key (3072 or 4096 bits). Select a file available to the execution machine. |
| Private-key password | `private_key_password` | Password | Optional passphrase for an encrypted PEM private key. Leave blank for an unencrypted key. |
| Data mode | `data_mode` | Choice | Choose which source to read. |
| Saved-search ID (Saved search mode) | `saved_search_id` | Text | Required for Saved search only. Internal ID or script ID; requires REST saved-search support (September 2026.2 or later). |
| SuiteQL query (SuiteQL mode) | `suiteql` | Text | Required for SuiteQL only. For Full, use deterministic ordering with a unique tie-breaker. Do not include secrets. |
| Extraction mode | `extraction_mode` | Choice | Sample returns up to 100 rows. Full reads all pages within the documented size and time limits. |
| Output fields | `output_columns` | Text | Leave blank for all returned fields. To select fields, enter comma-separated names in output order, e.g. id, name. For an empty result, supply field names to define the output. |

Saved search and Sample are the defaults. Both source settings remain visible; only the selected mode's setting
is read. Connection values have no defaults. The optional password preserves the exact passphrase.

## Outputs

**Data** (`data`): one row per result, with all values returned as text or missing values.
Identifiers and decimal numbers retain their precision. Nested objects and arrays become JSON text.
Null and empty strings become missing; literal text `null` remains text. The top-level `links` metadata is omitted.

With Output fields blank, columns are discovered across the retained rows and sorted by name.
Comma-separated field names select and order columns after retrieval; missing selected fields are blank.
Legacy JSON arrays of field names are also accepted. Empty results require Output fields to define the schema.
Empty names, surrounding whitespace and case-insensitive name collisions are rejected.

## Limits

- Sample returns up to 100 rows. Full uses 1,000-row pages and requires fewer than 100,000 rows.
- Both modes allow 8 MiB per decoded response, 64 MiB in total and 15 minutes including authentication and retries.
- Results accumulate in memory; memory use can exceed response size. Narrow the source if a limit is reached.
- Full extraction needs deterministic sorting with a unique tie-breaker. Offset paging is not a snapshot;
  changing source data can still produce omissions or duplicates.
- Each execution fetches the source again. There is no incremental cursor, table discovery or NetSuite write access.
- A failed extraction commits no output. Omniscope may retain an older successful result: check execution status.

## Why do this in Omniscope

Join the selected NetSuite results to orders, budgets or CRM exports in the same workflow, then convert the
required amount and date fields before aggregation. Keeping identifiers as text avoids losing long IDs before
a join. The script exposes the extraction and field-selection behaviour for maintainers to inspect.

The core **Database** block is an alternative when an appropriate JDBC driver and account entitlement are
available. This connector instead uses NetSuite REST, certificate authentication and an existing search or query.

## Try it

Before this contribution is merged, create a ZIP with only this folder's `manifest.json` and `script.py` at its root.
In a test workflow use **Add > Import custom script** to import it, then follow the [setup guide](customer-setup.md).
Importing the block does not require credentials; executing it does.
After publication, it can also be added from the Connectors category in the block picker.

[sample-data/placeholder.csv](sample-data/placeholder.csv) contains invented output matching a harness test.
It illustrates the output format, not a captured NetSuite response. Import identifier fields as text.
Import [demo.ioz](demo.ioz) into Omniscope. It contains an unconfigured NetSuite block and a separate
File → Validate data path using the invented CSV. **Run only Validate data** to check that sample's schema
and single row. The canvas explains that the NetSuite block requires customer credentials and has not run
against NetSuite. Configure it separately using the setup guide before attempting real extraction.
The export excludes project history and passwords; there is no demo-data switch in the connector.

## Language and libraries

Python 3.9-compatible syntax. Execution tests in this contribution use Python 3.11.
Omniscope supplies pandas and its Python API; the other direct dependencies are declared in the manifest.

| Library | Version requirement | Licence |
|---|---|---|
| requests | >=2.32.5,<3 | Apache 2.0 |
| PyJWT with crypto extra | >=2.10.1,<3 | MIT |
| simplejson | >=3.20.1,<4 | MIT |
| cryptography | Resolved through PyJWT's crypto extra | Apache 2.0 or BSD 3-Clause |
| pandas | Supplied by Omniscope | BSD 3-Clause |

The connector is contributed under the repository's MIT licence. NetSuite account and API entitlements
remain the administrator's responsibility. No third-party library source is bundled here.

The icon is an original generic connector glyph, not a NetSuite logo. Oracle's
[logo guidelines](https://www.oracle.com/legal/logos/) require authorization and prohibit modifying authorized
logos; permission for a recoloured NetSuite logo is unavailable for this contribution. The service is identified
in text under the repository's generic-icon exception. This connector is not endorsed by Oracle.
NetSuite is a registered trademark of Oracle and/or its affiliates.

## Validation status

The original standalone package recorded **116 passing offline tests** on 20 October 2026.
This repository adaptation has **119 passing offline tests**, including three additional shared-harness cases;
the standalone ZIP test is replaced by a manifest contract test because ZIP packaging is not part of this folder.
Run them from the repository root with `python3 -m pytest Connectors/NetSuite` after installing
`tools/python/requirements.txt`.

Tests use synthetic responses and temporary generated keys. Unmocked Requests sends fail the tests.
They cover signing, both query modes, pagination, retries, limits, safe errors, precise text output and lifecycle.
The shared harness also executes the actual entry point with manifest defaults, no upstream input, an empty
result and a failed request. These checks do not contact NetSuite.

Earlier Omniscope 2026.2 Dev checks imported the original package and used an injected synthetic transport
through the real runtime. They checked File/Password options, text and missing values, long IDs and empty output.
A fresh contribution check on 20 November 2026 imported the current block in Omniscope 2026.2 Dev.
A separate temporary probe injected synthetic HTTP responses into the current script and executed through
Omniscope's Python runtime. Query API results confirmed two text fields in the requested `name, id` order,
a precise 21-digit ID, and an empty name represented as missing. The exported demo's separate Validate data
path passed with one invented record and zero problems. The synthetic probe is not included in the demo.
Neither check validates a NetSuite account, Docker file mapping or dependencies on another execution host.

Before operational use, validate real M2M authentication, restricted-role permissions, both source modes,
stable multi-page reconciliation, empty results, credential rotation/revocation and scheduled re-execution
in the intended local or Docker environment. A successful import or HTTP response alone is insufficient.
