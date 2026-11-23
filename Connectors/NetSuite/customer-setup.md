# NetSuite Connector v0.1.0

This is a read-only Python Custom Block for Omniscope. It can retrieve a saved search or execute a SuiteQL
query. It has been built and tested with simulated responses, **without a NetSuite account**. Treat it as
a first validation package. See [validation status](README.md#validation-status) for the evidence and remaining checks.

## Try importing the block without NetSuite access

- Create a ZIP containing only `manifest.json` and `script.py` from this folder, at the archive root.
- Open a test workflow in Omniscope.
- Use **Add > Import custom script**, select the ZIP, then **Import**.
- Open the new NetSuite Connector block. Check the Connection, Data selection and Output sections.
- Confirm that Saved search and Sample are selected, and that the key is a File option and the password
  is masked. You need no NetSuite credentials just to import and inspect the block.

Executing a real extraction requires the administrator setup below. The block has no demo-data switch.
Python dependencies may be installed on first execution, so an import success does not establish that
the execution environment is ready.

## NetSuite administrator setup

Use an API-enabled account and a dedicated, restricted integration role with access to the intended data.
Check REST Web Services, SuiteAnalytics Workbook and OAuth 2.0 features, together with the role permissions
in Oracle's [REST prerequisites](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_5085602973.html).
Avoid using an Administrator role for ongoing extraction. Account features and data permissions vary.

Create an OAuth 2.0 integration application with **Client Credentials (Machine to Machine)** enabled and
the `rest_webservices` scope. Record its client ID. This flow uses a certificate and matching private key;
the connector does not need a client secret, username/password login or browser callback.

Create a 3072-bit or 4096-bit RSA key with a matching X.509 certificate. This connector signs with PS256.
Follow Oracle's [certificate conditions](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/subsect_162755332391.html);
its RSA-PSS OpenSSL example is suitable. If encrypting the private key, retain its exact passphrase.
Store the private key on the Omniscope execution machine with restricted file permissions. Upload only
the public certificate to NetSuite; do not include the private key in the block ZIP or send it to support.

In **Setup > Integration > Manage Authentication > OAuth 2.0 Client Credentials (M2M) Setup**, create the
application/entity/role mapping and upload the certificate. Copy the resulting certificate ID.
See Oracle's [mapping instructions](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_162686838198.html).
Each account needs its own mapping; sandbox refreshes clear the setup. Monitor certificate expiry and
rotate by creating the replacement mapping and updating the key file and certificate ID together.

Copy the account-specific SuiteTalk URL from **Company Information > Company URLs**.
Use the HTTPS origin only, for example `https://123456-sb1.suitetalk.api.netsuite.com`.
Do not append a REST path, query string or fragment. A separate account ID is unnecessary.
See [account-specific URLs](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1546938065.html).

The implementation requires no paid third-party driver. The customer's actual NetSuite API and user
entitlements remain an administrator check.

## Omniscope execution environment

Use Python 3.9 or later. The script uses `requests`, `PyJWT[crypto]`, `simplejson`, pandas and the Omniscope
Python API. The ZIP declares the first three; Omniscope supplies its API and pandas as runtime components.
The manifest records bounded dependency ranges. See the [README](README.md#language-and-libraries) for dependency ranges.

Select the private key with the **Private-key file** option. The script reads the runtime path returned by
Omniscope. For Docker execution, this File option supplies the read-only mount; a text field containing
a host path would not do that. Confirm the service account can read the file and the execution environment
can reach NetSuite over HTTPS.

See [Custom Block setup](https://help.visokio.com/support/solutions/articles/42000071133) and
[Docker execution](https://help.visokio.com/support/solutions/articles/42000089057).
Docker mode is a server setting affecting Custom Blocks generally. Do not change that setting solely to
import this package. Local execution shares installed dependencies with other Custom Blocks.

Standard proxy environment variables are honoured. TLS verification remains enabled; the connector does not
use ambient `.netrc` login credentials. If a corporate TLS gateway requires a custom trust store, arrange
that in the Python environment with your administrator; do not disable certificate verification.

## Select data and validate it

**Saved search:** supply its internal ID or script ID. The mapped role must be able to use the search.
REST saved-search support was introduced in the September NetSuite 2026.2 release; confirm account availability.
The connector cannot change the search's filters or sorting. Use a search with a stable order and a unique
tie-breaker for Full mode. [Oracle saved-search contract](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0804090827.html)

**SuiteQL:** paste a known query approved by your NetSuite administrator. The query is sent unchanged.
For Full mode include deterministic ordering with a unique tie-breaker. No parameter-entry UI or automatic
query rewriting is provided. Do not put secrets in the query.
[Oracle SuiteQL contract](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_157909186990.html)

Only the field for the selected mode is used.

- Start with **Sample**: at most 100 rows, always labelled Sample.
- Compare identifiers, row values and representative amounts with NetSuite under the same role.
- Try **Full** on a small, stable source with more than 1,000 rows. Reconcile its count and values.
- Test empty results, denied permissions, revoked credentials, scheduled re-execution and your intended
  local/Docker environment before using it operationally.

## Output and limits

There is one Data output. Values are text, with JSON null kept as missing. IDs and decimal values are not
converted through floating-point numbers. **Empty strings also become missing values**, following Omniscope's
normal text-import behaviour. Literal `"null"` remains text. Nested objects and arrays become JSON text,
preserving empty strings inside them. Convert types downstream where appropriate.

The top-level field `links` is reserved for API metadata and omitted. Nested `links` values are retained.
Column names retain their spelling and are sorted by default. Empty names, surrounding whitespace and
case-insensitive collisions are rejected rather than silently renamed.

**Output fields:** leave blank to return all fields supplied by the saved search or query. After setting up
the connection, selecting Saved search and entering its ID is enough to execute with the default Sample mode.
To select particular fields and their order, enter a comma-separated list, for example `id, name`.
Unselected fields are omitted; absent selected fields become missing. This selection happens after retrieval.
An empty result requires field names because the API has supplied no rows from which to infer a schema.
The original JSON-array format remains accepted for existing configurations.

Both source inputs remain visible because the Custom Block manifest has no conditional-visibility setting.
Only the input matching Data mode is used; leave the other blank.

Full mode uses 1,000-row pages and requires **fewer than 100,000 rows**, including when the API reports exactly
100,000 with no further page. This conservative boundary avoids claiming a capped result is complete.
Both modes have an 8 MiB decoded response limit, 64 MiB total decoded-response budget and a 15-minute
execution deadline, including token requests, waits and retries. Narrow the source if these limits are reached.
Rows are accumulated in memory; actual memory use can be substantially larger than the response bytes.

Offset paging is not a transactional snapshot. Stable sorting and count checks cannot prevent all omissions
or duplicates if the source changes during extraction. Validate against stable data.

Re-execution fetches the source again. Use Omniscope scheduling for refreshes; this version stores no
incremental cursor. Failed attempts do not commit an extract. Omniscope may still show data from a previous
successful run, so always check execution status.

## Troubleshooting and support

| Message | Administrator check |
|---|---|
| Invalid configuration/key | URL, selected source, PEM RSA size, file access and exact passphrase |
| Authentication rejected | Application, certificate ID, key pairing, mapping, expiry and machine clock |
| HTTP 403 / Access denied | Role/data access and network policy; the code alone does not establish the cause |
| HTTP 404 / Source unavailable | Search ID, role visibility and account release |
| Invalid query/search request | Run the same source under the mapped role and correct its definition |
| Rate limit exhausted | Retry later; account limits are shared with other integrations |
| Network/TLS failure | DNS, HTTPS access, proxy and trusted certificate chain |
| Unexpected response / incomplete extract | Keep the stage/status/code; check stability, limits and actual API shape |
| Execution time limit | Narrow the source; the process exits unsuccessfully and its transaction is discarded |

Support evidence should contain package version, safe stage/status/code, counts and sanitised administrator
findings. Never send a private key, access token, passphrase or confidential query/results. The connector
deliberately does not print raw API responses, configured values or exception details.
