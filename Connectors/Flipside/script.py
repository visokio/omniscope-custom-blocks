"""Flipside: runs a SQL query on Flipside's blockchain data through the Flipside Python SDK and writes every page
of the result. Flipside has wound down its public tools (see README.md): the API may no longer accept queries."""
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import pandas as pd
from flipside import Flipside
from flipside.errors import (ApiError, QueryRunCancelledError, QueryRunExecutionError, QueryRunRateLimitError,
                             QueryRunTimeoutError, SDKError, ServerError)

PAGE_SIZE = 10000

key = omniscope_api.get_option("key")
key = "" if key is None else str(key).strip()
sql = omniscope_api.get_option("query")
sql = "" if sql is None else str(sql).strip()
if not key:
    omniscope_api.abort("Enter your Flipside API key.")
if not sql:
    omniscope_api.abort("Enter the SQL query to run.")

sdk = Flipside(key)


def reason(e):
    # The SDK's query errors carry .message; ApiError does not, so fall back to its text
    return getattr(e, "message", None) or str(e)


def frame(records, columns=None):
    df = pd.DataFrame(records or [], columns=columns if not records else None)
    return df.drop(columns=["__row_index"], errors="ignore")


try:
    omniscope_api.update_message("Submitting query...")
    result = sdk.query(sql, max_age_minutes=0, timeout_minutes=20, retry_interval_seconds=1,
                       page_size=PAGE_SIZE, page_number=1)
    columns = [c for c in (getattr(result, "columns", None) or []) if c != "__row_index"]

    # The first page comes with the query result; read the next pages until one is short or empty
    pages = [frame(getattr(result, "records", None) or [])]
    page_number = 1
    while len(pages[-1]) == PAGE_SIZE:
        page_number += 1
        omniscope_api.update_message(f"Retrieving records (page {page_number})")
        page = sdk.get_query_results(result.query_id, page_number=page_number, page_size=PAGE_SIZE)
        pages.append(frame(getattr(page, "records", None) or []))

    data = pd.concat([p for p in pages if len(p)], ignore_index=True) if any(len(p) for p in pages) \
        else frame([], columns)
    omniscope_api.write_output_records(data, output_number=0)
    omniscope_api.close(f"Retrieved {len(data)} records.")

except QueryRunRateLimitError as e:
    omniscope_api.abort(f"You have been rate limited: {reason(e)}")
except QueryRunTimeoutError as e:
    omniscope_api.abort(f"Your query has taken longer than the specified timeout to run: {reason(e)}")
except (QueryRunExecutionError, QueryRunCancelledError) as e:
    omniscope_api.abort(f"Flipside could not run the query: {reason(e)}")
except ServerError as e:
    omniscope_api.abort(f"A server-side error has occurred: {reason(e)}")
except (ApiError, SDKError) as e:
    omniscope_api.abort(f"An API error has occurred: {reason(e)}")
except OSError as e:  # connection errors (requests' errors are OSErrors): the service may no longer be running
    omniscope_api.abort(f"Could not reach Flipside ({type(e).__name__}). Flipside has wound down its public "
                        "query service; see the block's README.")
