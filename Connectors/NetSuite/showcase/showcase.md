# NetSuite Connector

*Omniscope custom block · Connectors*

Read a NetSuite saved search or SuiteQL result into a workflow for joining, preparation and reporting.
**Evaluation version 0.1.0: no live NetSuite account has been tested. Production readiness is not established.**

## The problem it solves

A finance workflow may need NetSuite results alongside budgets or CRM data. This block retrieves the chosen
search or query through REST, using a certificate-based integration identity configured by your administrator.

## What goes in

No upstream data. Supply your account's SuiteTalk URL, application client ID, certificate ID and private-key
file, plus a saved-search ID or SuiteQL query. Saved-search REST needs the September NetSuite 2026.2 feature
or later. Account permissions determine which results are accessible.

## The options

Start with the default Saved search and Sample settings. Sample returns up to 100 rows.
For SuiteQL, select that mode and enter an administrator-approved query instead.
Leave Output fields blank for all returned fields, or enter comma-separated names to select and order them.
An empty result requires field names to define its output schema.

## What comes out

One Data output, with values as text or missing. Nested values become JSON text.
The invented sample output has these fields; it is not data retrieved from NetSuite:

| amount | id | name |
|---|---|---|
| 123.45 | 123456789012345678901 | Example |

## Where it pays off

After validating the connector against your account, join a known transaction extract to a budget file,
convert amount fields to numbers and compare totals. Keep identifiers as text when joining to other systems.

## How it fits into an Omniscope workflow

NetSuite Connector → field type conversion → Join with budgets → Aggregate → Report.
Full mode reads sequential pages within the size and time limits and requires fewer than 100,000 rows.
Stable ordering is required; offset paging cannot guarantee a snapshot while records change.

## Try it

Follow the [setup guide](../customer-setup.md) to configure authentication and import the block.
Begin with a small source whose results you can reconcile with NetSuite under the mapped role.
Import [demo.ioz](../demo.ioz) and run only its Validate data block to check the separate invented sample.
The NetSuite block is deliberately unconfigured: actual execution requires customer credentials.
The canvas labels this distinction; no sample result is evidence of a live NetSuite extraction.

## Tested

The contribution passes 119 offline tests with synthetic responses, including the shared Omniscope API harness.
A fresh Omniscope runtime probe with synthetic responses confirmed requested field order, exact long IDs
and missing values. The demo's separate sample validation also passed.
No real NetSuite authentication or extraction has been tested. See the
[README](../README.md#validation-status) for the exact distinction and remaining acceptance checks.
