from collections import Counter

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

CURRENT, NEW = "current name", "new name"

# The rules come from the "Rename rules" text option when it is filled in, otherwise from the CSV file option.
# (A streaming block has exactly one input, so the rules can't arrive as a second, rules-table input.)
rules_text = omniscope_api.get_option("rulesText")
rules_text = str(rules_text) if rules_text is not None else ""
rules_file_path = omniscope_api.get_option("rules")

if rules_text.strip():
    # One rule per line, or rules separated by semicolons: Current Name = New Name
    pairs = []
    for part in rules_text.replace("\r", "\n").replace(";", "\n").split("\n"):
        if not part.strip():
            continue
        if "=" not in part:
            omniscope_api.abort(f"Write each rule as Current Name = New Name; this one has no '=': {part.strip()}")
        current, new = part.split("=", 1)
        pairs.append((current.strip(), new.strip()))
    current_names = pd.Series([c for c, _ in pairs], dtype=object)
    new_names = pd.Series([n for _, n in pairs], dtype=object)
else:
    if not rules_file_path:
        omniscope_api.abort("Write the rename rules in the Rename rules option, or choose a rename rules CSV file.")
    try:
        # utf-8-sig drops the byte order mark some spreadsheet programs write at the start of a CSV file.
        rename_rules = pd.read_csv(rules_file_path, dtype=str, keep_default_na=False, skipinitialspace=True,
                                   encoding="utf-8-sig")
    except Exception as e:  # noqa: BLE001 - any read error is reported to the user the same way
        omniscope_api.abort(f"Could not read the rename rules file {rules_file_path}: {e}")

    # Find the two columns by name, ignoring capitals and spaces at either end.
    columns = {str(c).strip().lower(): c for c in rename_rules.columns}
    if CURRENT not in columns or NEW not in columns:
        omniscope_api.abort("The rename rules file must have the columns 'Current Name' and 'New Name'; it has: "
                            + ", ".join(str(c) for c in rename_rules.columns))
    current_names = rename_rules[columns[CURRENT]].str.strip()
    new_names = rename_rules[columns[NEW]].str.strip()

# A rule with no current name renames nothing (blank lines, for example); a rule with no new name is a mistake.
keep = current_names != ""
current_names, new_names = current_names[keep], new_names[keep]
if (new_names == "").any():
    omniscope_api.abort("These rules have no new name: " + ", ".join(current_names[new_names == ""].unique()))
duplicated = current_names[current_names.duplicated()].unique()
if len(duplicated):
    omniscope_api.abort("The rules name these current fields more than once: " + ", ".join(duplicated))

rename_map = dict(zip(current_names, new_names))


def renamed_columns(columns):
    """The new field names, or an abort if two fields would end up with the same name."""
    result = [rename_map.get(c, c) for c in columns]
    clashes = sorted(c for c, n in Counter(result).items() if n > 1)
    if clashes:
        omniscope_api.abort("Renaming would give two fields the same name: " + ", ".join(clashes))
    return result


def handle_chunk(chunk):
    # The same rules give the same names on every chunk, so the output schema never changes.
    return chunk.set_axis(renamed_columns(list(chunk.columns)), axis=1)


omniscope_api.process_stream(handle_chunk)

# The data stream is over: no more data can be read or written.
omniscope_api.close()
