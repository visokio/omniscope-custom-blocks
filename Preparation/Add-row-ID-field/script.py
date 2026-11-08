from omniscope.api import OmniscopeApi
import pandas as pd

omniscope_api = OmniscopeApi()

DEFAULT_NAME = "Row ID"

field_name = omniscope_api.get_option("fieldName")
field_name = str(field_name).strip() if field_name is not None else ""
if not field_name:
    field_name = DEFAULT_NAME

start_at = omniscope_api.get_option("startAt")
if start_at is None or start_at == "":
    start_at = 1
try:
    start_at = int(start_at)
except (TypeError, ValueError):
    omniscope_api.abort(f"Start at must be a whole number, not {start_at!r}.")

put_first = bool(omniscope_api.get_option("putFirst"))

# The number the next record gets. The data arrives in chunks, in order, and the count carries on from one chunk
# to the next, so the IDs run 1..N over the whole input with no gaps or repeats.
next_id = start_at


def handle_chunk(chunk):
    global next_id
    ids = pd.Series(range(next_id, next_id + len(chunk)), index=chunk.index, dtype="int64")
    next_id += len(chunk)

    if field_name in chunk.columns:
        # An existing field of the same name is replaced (in place, unless the ID is put first).
        chunk = chunk.copy()
        chunk[field_name] = ids
        if put_first:
            chunk = chunk[[field_name] + [c for c in chunk.columns if c != field_name]]
        return chunk
    if put_first:
        return pd.concat([ids.rename(field_name).to_frame(), chunk], axis=1)
    return chunk.assign(**{field_name: ids})


omniscope_api.process_stream(handle_chunk)

# The data stream is over: no more data can be read or written.
omniscope_api.close()
