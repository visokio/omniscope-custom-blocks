# AirTable connector

Fetch all records from an AirTable table using the AirTable REST API.

## Usage
Provide a personal access token, base ID, and table name or ID. Optionally set the page size (1-100). Records are automatically
paginated and written to the block output as a dataframe.

Complex field types (arrays or objects) are serialized to JSON strings to ensure compatibility with Omniscope.
