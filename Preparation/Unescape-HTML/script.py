"""Unescape HTML: turns HTML character references (&amp; &eacute; &#163; ...) in one field back into the characters
they stand for, in a new field."""
import html

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

field_name = omniscope_api.get_option("fieldName")
output_field = (omniscope_api.get_option("outputField") or "").strip() or "Unicode text"
repeat = bool(omniscope_api.get_option("repeat"))
plain_spaces = bool(omniscope_api.get_option("plainSpaces"))

if not field_name:
    omniscope_api.abort("Choose the field to unescape (Text to unescape).")


def unescape(value):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = value if isinstance(value, str) else str(value)
    result = html.unescape(text)
    # double-escaped text (&amp;lt; for <) needs more than one pass; stop when nothing changes
    passes = 1
    while repeat and result != text and passes < 10:
        text, result = result, html.unescape(result)
        passes += 1
    if plain_spaces:
        result = result.replace("\u00a0", " ")
    return result


def handle_chunk(chunk):
    if field_name not in chunk.columns:
        omniscope_api.abort(f"The field '{field_name}' is not in the input.")
    if output_field != field_name and output_field in chunk.columns:
        omniscope_api.abort(f"The input already has a field called '{output_field}'. "
                            "Choose another name, or the name of the field being unescaped to replace it.")
    chunk[output_field] = pd.Series([unescape(v) for v in chunk[field_name]], index=chunk.index, dtype=object)
    return chunk


# The records are processed in chunks; each record is unescaped on its own, so chunking does not change the result.
omniscope_api.process_stream(handle_chunk)
omniscope_api.close()
