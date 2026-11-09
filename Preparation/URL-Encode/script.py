"""URL Encode: percent-encodes the text in one field (UTF-8) into a new field, ready to put in a link or a request."""
import urllib.parse

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

field_name = omniscope_api.get_option("fieldName")
output_field = (omniscope_api.get_option("outputField") or "").strip() or "Quoted text"
encode_slashes = bool(omniscope_api.get_option("encodeSlashes"))
spaces_as_plus = bool(omniscope_api.get_option("spacesAsPlus"))

if not field_name:
    omniscope_api.abort("Choose the field to encode (Text to encode).")

# quote() leaves letters, digits and _ . - ~ as they are, plus the characters in `safe`
safe = "" if encode_slashes else "/"
quote = urllib.parse.quote_plus if spaces_as_plus else urllib.parse.quote


def encode(value):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return quote(value if isinstance(value, str) else str(value), safe=safe)


def handle_chunk(chunk):
    if field_name not in chunk.columns:
        omniscope_api.abort(f"The field '{field_name}' is not in the input.")
    if output_field != field_name and output_field in chunk.columns:
        omniscope_api.abort(f"The input already has a field called '{output_field}'. "
                            "Choose another name, or the name of the field being encoded to replace it.")
    chunk[output_field] = pd.Series([encode(v) for v in chunk[field_name]], index=chunk.index, dtype=object)
    return chunk


# The records are processed in chunks; each record is encoded on its own, so chunking does not change the result.
omniscope_api.process_stream(handle_chunk)
omniscope_api.close()
