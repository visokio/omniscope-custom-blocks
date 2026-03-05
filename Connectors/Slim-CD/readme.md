# Slim CD connector

This block is a simple connector that pulls transaction records from the Slim CD gateway and outputs them as a table in Omniscope.

What it does:
- Connects to Slim CD reporting endpoint and runs the SearchTransactions2 service call

Requires only:
- Username
- Password
- Site ID

Lets the user optionally set:
- Date range (startdate, enddate) to limit the query
- Result controls: maxrecords, reverseorder
- Filters: name, email, city/state/zip, amount, transaction reference, transaction type, clerk name, gate ID, and card-related fields (as supported by SlimCD)

Outputs:
- A Transactions dataset (one row per transaction returned), ready for analysis/joins/visualizations in Omniscope.
- If Record count only is enabled, it outputs a single row with the total record count instead of returning transaction rows (useful to sanity-check volume before pulling a large range).

In short: it turns SlimCD transaction search results into a clean Omniscope table, with the same kinds of filters you’d use in the gateway UI.

