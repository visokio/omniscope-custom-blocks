from omniscope.api import OmniscopeApi
import numpy as np
import pandas as pd
import json
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the data with the JSON field to the block's input.")

jsonField = omniscope_api.get_option("jsonField")
includeInput = omniscope_api.get_option("includeInput")
includeInput = includeInput is None or includeInput is True or str(includeInput).lower() == "true"

if not jsonField:
    omniscope_api.abort("Choose the field holding the JSON text in 'JSON field'.")
if jsonField not in input_data.columns:
    omniscope_api.abort(f"The input has no field called '{jsonField}'.")


def to_records(value):
    """The JSON in one cell as a list of objects: an object is one record, an array one record per item
    (an item that is not an object goes in a field called 'value'). None for empty or invalid JSON."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return False
    items = parsed if isinstance(parsed, list) else [parsed]
    return [item if isinstance(item, dict) else {"value": item} for item in items]


def tidy(s: pd.Series) -> pd.Series:
    """One field's values: numbers stay numbers, true/false stay yes/no, anything else (or a mix) becomes text;
    arrays left inside a record become JSON text."""
    values = [None if (not isinstance(v, (list, dict)) and pd.isna(v)) else v for v in s]
    present = [v for v in values if v is not None]
    if present and all(isinstance(v, (bool, np.bool_)) for v in present):
        return pd.Series(values, index=s.index, dtype="boolean")
    if present and all(isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))
                       for v in present):
        if all(float(v).is_integer() for v in present) and all(isinstance(v, (int, np.integer)) for v in present):
            return pd.Series(values, index=s.index, dtype="Int64")
        return pd.Series([None if v is None else float(v) for v in values], index=s.index, dtype="float64")

    def text(v):
        if v is None:
            return None
        if isinstance(v, (list, dict)):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, (bool, np.bool_)):
            return "true" if v else "false"
        return str(v)
    return pd.Series([text(v) for v in values], index=s.index, dtype=object)


# Flatten every record's JSON into one list of objects, remembering the input record each came from
rows = []
source = []
bad = 0
for pos, value in enumerate(input_data[jsonField]):
    records = to_records(value)
    if records is False:
        bad += 1
    if records:
        rows.extend(records)
        source.extend([pos] * len(records))
    elif includeInput:
        source.append(pos)  # keep the input record once, with empty JSON fields
        rows.append({})



def flatten(obj, prefix=""):
    """Nested objects become fields joined with a dot (customer.name), as pandas' json_normalize does;
    arrays inside a record are kept as they are. Values keep their JSON types (int stays int)."""
    out = {}
    for k, v in obj.items():
        name = f"{prefix}{k}"
        if isinstance(v, dict) and v:
            out.update(flatten(v, name + "."))
        else:
            out[name] = v
    return out


flat = pd.DataFrame([flatten(r) for r in rows], index=range(len(rows)), dtype=object)
flat = flat.add_prefix(jsonField + '_')
for c in flat.columns:
    flat[c] = tidy(flat[c])

if includeInput:
    clash = [c for c in flat.columns if c in input_data.columns]
    if clash:
        omniscope_api.abort("These JSON fields have the same name as input fields: " + ", ".join(clash[:10]))
    # Repeat the input fields for each record made from them, keeping their types
    repeated = input_data.iloc[np.asarray(source, dtype=np.int64)].reset_index(drop=True)
    output_data = pd.concat([repeated, flat.reset_index(drop=True)], axis=1)
else:
    output_data = flat.reset_index(drop=True)

if output_data.shape[1] == 0:
    omniscope_api.abort("No JSON found in the field, so there are no fields to output.")

#write the output records in the first output
omniscope_api.write_output_records(output_data, output_number=0)
if bad:
    omniscope_api.close(f"{bad} record(s) had text that is not valid JSON; their JSON fields are empty.")
else:
    omniscope_api.close()
