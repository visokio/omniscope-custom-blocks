# HubSpot

Loads HubSpot companies, contacts, leads, deals, lists, forms, form submissions and associations into records, following every page, or searches contacts and companies.

A HubSpot account holds the sales and marketing side of a business: who the customers are, which deals are open, who filled in which form. This block brings those records into a workflow through HubSpot's APIs, one action per block, so they can be joined to orders, finance or support data and reported on.

- **Companies, Contacts, Leads, Deals**: every record (100 per request, every page), with the **properties** you list, or HubSpot's defaults.
- **Search contacts** or **Search companies** by a text, such as a surname or an e-mail domain.
- **Lists**, **Forms**, and the **Form submissions** of one form (one field per form question).
- **Associations**: which records of one object are linked to which of another, such as contacts to companies, one record per link.
- HubSpot's **timestamps become dates** (UTC). Property values stay as HubSpot sends them: text, even for numbers.
- When HubSpot's rate limit is hit, the block waits and tries again.

## HubSpot access

The block signs in with the access token of a HubSpot private app that has the read scopes for the objects you load (such as `crm.objects.contacts.read`). HubSpot stopped new private apps being created on 26 October 2026; existing ones, now listed as legacy apps under Settings > Integrations, keep working. For a new connection HubSpot directs customers to Service Keys (Settings > Integrations > Service Keys); the block sends its token as a bearer token, but it has not been tested with a service key.

The token can read everything its scopes allow in the account: give it only the read scopes you need.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from HubSpot.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Private app access token | `key` | Password | The access token of a HubSpot private app (Settings > Integrations > Private apps), with read scopes for the objects you load. |
| Action | `object` | Choice | Companies (default), Contacts, Leads, Deals, Lists, Forms, Form submissions, Search contacts, Search companies, or Associations between objects. |
| Search text or form ID | `params` | Text | For the searches, the text to look for. For Form submissions, the form's ID (from the Forms action). |
| Properties | `properties` | Text | Optional, comma-separated property names for Companies, Contacts, Leads, Deals and the searches, such as `name, domain, industry`. Empty: HubSpot's defaults (contacts: e-mail, first and last name, lifecycle stage). |
| From object | `from_object_type` | Text | For Associations: the object type to start from, such as `contacts` (default), `companies`, `deals`. |
| To object | `to_object_type` | Text | For Associations: the object type to find links to (default `companies`). |
| From object IDs | `object_ids` | Text | For Associations, optional: comma-separated record IDs. Empty: every record of the From object. |

## Outputs

- **Records** (`Output Data`): depends on the action.
  - Companies, Contacts, Leads, Deals and the searches: `id`, `createdAt`, `updatedAt`, `archived`, and one `properties.<name>` field per property.
  - Associations: `<from>_id`, `<to>_id`, `association_type` (for example `contacts_id`, `companies_id`).
  - Form submissions: `conversionId`, `submittedAt` (milliseconds since 1970, as HubSpot sends it), `pageUrl`, then one field per form question.
  - Lists and Forms: their HubSpot fields; nested parts (a list's filters, a form's field groups) as JSON text.

An action that finds nothing finishes with "HubSpot returned no records" and no output records.

## Limits

- A search returns at most 10,000 records (HubSpot's limit for its search API).
- Property values are text: convert amounts and counts with Field Organiser.
- Forms and Form submissions use HubSpot's older forms (v2) and form-integrations (v1) endpoints; the other actions use the CRM v3 API.
- In tests, 20,000 companies over 200 canned pages took under a second; against HubSpot, expect one request per 100 records, within HubSpot's rate limit for private apps.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented HubSpot responses (`tests/canned/`, written by `tests/make_canned.py`); `sample-data/placeholder.csv` is the Records output for the invented companies, for trying a workflow without a HubSpot account.
