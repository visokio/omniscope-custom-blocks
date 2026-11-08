"""Append PDF files: combines the PDF files listed in the input, in record order, into one PDF file."""
import os

import pandas as pd
from omniscope.api import OmniscopeApi
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

omniscope_api = OmniscopeApi()

input_data = omniscope_api.read_input_records(input_number=0)
input_folder = omniscope_api.get_option("input_folder")
name_field = omniscope_api.get_option("pdf_file_names")
title_field = omniscope_api.get_option("title")
output_folder = omniscope_api.get_option("output_folder")
file_name = omniscope_api.get_option("file_name")

if input_data is None:
    omniscope_api.abort("Connect a block whose records list the PDF files to combine.")
if not name_field:
    omniscope_api.abort("Choose the field holding the PDF file names.")
if not file_name or not str(file_name).strip():
    omniscope_api.abort("Enter a name for the combined PDF file.")

# The folder option is a file picker: accept a file chosen inside the folder as well as the folder itself.
if input_folder and os.path.isfile(input_folder):
    input_folder = os.path.dirname(input_folder)
if output_folder and os.path.isfile(output_folder):
    output_folder = os.path.dirname(output_folder)


def is_missing(value):
    return value is None or (not isinstance(value, str) and pd.isna(value)) or str(value).strip() == ""


paths = []
for position, value in enumerate(input_data[name_field].tolist(), start=1):
    if is_missing(value):
        omniscope_api.abort(f"Record {position} has no PDF file name.")
    name = str(value).strip()
    paths.append(name if os.path.isabs(name) or not input_folder else os.path.join(input_folder, name))

missing = [p for p in paths if not os.path.isfile(p)]
if missing:
    shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
    omniscope_api.abort(f"{len(missing)} PDF file(s) not found: {shown}")

file_name = str(file_name).strip()
if not file_name.lower().endswith(".pdf"):
    file_name += ".pdf"
if not output_folder:
    output_folder = input_folder or (os.path.dirname(paths[0]) if paths else "")
if not output_folder:
    omniscope_api.abort("Choose the output folder.")
output_file = os.path.join(output_folder, file_name)

output_data = input_data.copy()
if len(paths) == 0:
    output_data["Combined PDF"] = pd.Series(dtype=object)
    output_data["Pages"] = pd.Series(dtype="Int64")
    output_data["First page"] = pd.Series(dtype="Int64")
    omniscope_api.write_output_records(output_data, output_number=0)
    omniscope_api.commit("No records: no PDF file was written.")
    raise SystemExit

titles = input_data[title_field].tolist() if title_field else [None] * len(paths)
writer = PdfWriter()
pages, first_pages = [], []
for path, title in zip(paths, titles):
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            omniscope_api.abort(f"{path} is password-protected; remove the password before combining it.")
        first_pages.append(len(writer.pages) + 1)
        writer.append(reader, outline_item=None if is_missing(title) else str(title))
        pages.append(len(reader.pages))
    except (PdfReadError, ValueError, OSError) as error:
        omniscope_api.abort(f"Could not read {path} as a PDF: {error}")

os.makedirs(output_folder, exist_ok=True)
with open(output_file, "wb") as fh:
    writer.write(fh)
writer.close()

output_data["Combined PDF"] = output_file
output_data["Pages"] = pd.array(pages, dtype="Int64")
output_data["First page"] = pd.array(first_pages, dtype="Int64")
omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.commit(f"Combined {len(paths)} PDF file(s), {sum(pages)} pages, into {output_file}")
