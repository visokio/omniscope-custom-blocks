from omniscope.api import OmniscopeApi
import markdown, pandas as pd
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the data with the Markdown text to the block's input.")

md_field = omniscope_api.get_option('MarkdownText')
output_field = (omniscope_api.get_option('outputField') or "HTML").strip() or "HTML"
keep_input = omniscope_api.get_option('includeInput')
keep_input = keep_input is None or keep_input is True or str(keep_input).lower() == "true"
extras = omniscope_api.get_option('extensions')
extras = extras is None or extras is True or str(extras).lower() == "true"

if not md_field:
    omniscope_api.abort("Choose the field holding the Markdown text in 'Markdown field'.")
if md_field not in input_data.columns:
    omniscope_api.abort(f"The input has no field called '{md_field}'.")
if keep_input and output_field in input_data.columns and output_field != md_field:
    omniscope_api.abort(f"The input already has a field called '{output_field}'. Choose another 'HTML field name'.")

# 'extra' adds tables, fenced code blocks, footnotes, abbreviations, definition lists and attribute lists
converter = markdown.Markdown(extensions=['extra'] if extras else [])


def to_html(text):
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return None
    converter.reset()
    return converter.convert(str(text))


# Each distinct text is converted once
cache = {}
htmls = []
for v in input_data[md_field]:
    key = v if isinstance(v, str) else (None if pd.isna(v) else str(v))
    if key not in cache:
        cache[key] = to_html(key)
    htmls.append(cache[key])

if keep_input:
    output_data = input_data.copy()
    output_data[output_field] = pd.Series(htmls, index=input_data.index, dtype=object)
else:
    output_data = pd.DataFrame({output_field: pd.Series(htmls, dtype=object)})

#write the output records in the first output
omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
