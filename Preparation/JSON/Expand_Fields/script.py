from omniscope.api import OmniscopeApi
import pandas as pd
import json

# Initialize Omniscope API
omniscope_api = OmniscopeApi()

# Read the records associated with the first block input
input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the data with the JSON field to the block's input.")

# Get options
jsonField = omniscope_api.get_option("jsonField")
includeInput = omniscope_api.get_option("includeInput")
prefix = omniscope_api.get_option("fieldPrefix") or ""

if not jsonField:
    omniscope_api.abort("Choose the field holding the JSON text in 'JSON field'.")
if jsonField not in input_data.columns:
    omniscope_api.abort(f"The input has no field called '{jsonField}'.")
includeInput = includeInput is None or includeInput is True or str(includeInput).lower() == "true"


def parse_json(value):
    """The top-level keys of a JSON object, or None for empty text, invalid JSON, or JSON that is not an object."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return False
    return parsed if isinstance(parsed, dict) else False


def as_text(v):
    """Nested objects and arrays become JSON text; other values their usual text."""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def tidy(values):
    """One field's values: numbers stay numbers, true/false stay yes/no, anything else (or a mix) becomes text."""
    present = [v for v in values if v is not None]
    if present and all(isinstance(v, bool) for v in present):
        return pd.Series(values, dtype="boolean")
    if present and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        if all(isinstance(v, int) for v in present) and all(abs(v) < 2 ** 63 for v in present):
            return pd.Series(values, dtype="Int64")
        return pd.Series([float(v) if v is not None else None for v in values], dtype="float64")
    return pd.Series([as_text(v) if v is not None else None for v in values], dtype=object)


parsed = [parse_json(v) for v in input_data[jsonField]]
bad = sum(1 for p in parsed if p is False)

# Field names in order of first appearance, with the prefix
keys = []
seen = set()
for p in parsed:
    if p:
        for k in p:
            if k not in seen:
                seen.add(k)
                keys.append(k)

expanded = {}
for k in keys:
    expanded[f"{prefix}{k}"] = tidy([p.get(k) if p else None for p in parsed])
expanded_df = pd.DataFrame(expanded, index=input_data.index)

if includeInput:
    clash = [c for c in expanded_df.columns if c in input_data.columns]
    if clash:
        omniscope_api.abort("The JSON has keys with the same name as input fields: " + ", ".join(clash[:10])
                            + ". Set 'Prefix for new fields' (for example json_) to keep them apart.")
    output_data = pd.concat([input_data, expanded_df], axis=1)
else:
    output_data = expanded_df

if output_data.shape[1] == 0:
    omniscope_api.abort("No JSON objects found in the field, so there are no fields to output.")

# Write the output records in the first output (also when there are no records, so the next block sees the fields)
omniscope_api.write_output_records(output_data, output_number=0)

# Close the Omniscope API
if bad:
    omniscope_api.close(f"{bad} record(s) had text that is not a JSON object; their new fields are empty.")
else:
    omniscope_api.close()
