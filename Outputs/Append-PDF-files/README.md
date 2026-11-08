# Append PDF files

Combines the PDF files listed in the input records, in record order, into one PDF file, with an optional bookmark for each file.

Report packs, statements and document bundles are often made one PDF at a time: a cover, a section per department, an appendix, or one PDF per customer. This block puts them together into a single file on the Omniscope server.

- Each input record names one PDF file: a **file name** in the chosen folder, or a **full path**.
- The files are combined **in record order**, so sort the records first to change the order.
- With a **bookmark title** field, each file gets a bookmark (an entry in the PDF's outline) at its first page. Records with an empty title get none.
- The output is the input records with the **combined file's path**, each file's **page count** and the **page it starts on**, ready for a table of contents or an email block.
- The block stops with a message, before writing anything, if a file is missing, is not a PDF or is password-protected.

## Language and libraries

Python, with pypdf (BSD 3-Clause) to read and write the PDF files and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs pypdf with pip on first run (the manifest's `dependencies`).

## Inputs

- **Input 1**: one record per PDF file, with a field holding its file name or full path, and optionally a field of bookmark titles.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Folder of the PDF files | `input_folder` | File | The folder holding the PDF files (choosing a file inside it also works). Empty if the file name field holds full paths. |
| PDF file names | `pdf_file_names` | Field (text) | One PDF file name, or full path, per record. |
| Bookmark titles | `title` | Field | Optional: a bookmark title for each file. |
| Output folder | `output_folder` | File | The folder to write the combined PDF to. Empty: the folder of the PDF files. Created if missing. |
| Combined PDF file name | `file_name` | Text | The combined file's name, `combined.pdf` by default; `.pdf` is added if missing. An existing file of that name is replaced. |

## Outputs

- **Combined** (`Output Data`): the input records, plus Combined PDF (the combined file's full path), Pages (the file's page count) and First page (where it starts in the combined file).

With no input records, no file is written and the output has no records.

## Limits

- Password-protected PDFs are refused; remove the password first.
- Bookmarks already inside the source files are kept, under the new bookmark when there is one.
- In tests, 400 files of two pages each were combined in under a second.

## Source

[script.py](script.py)

The sample PDFs in `sample-data/pdfs/` (a fictional company's board pack, one file per section) and the list `sample-data/report-sections.csv` are invented and written by `sample-data/make_sample_pdfs.py`. `sample-data/placeholder.csv` is the block's Combined output for them (with the PDFs in a folder `/reports/pdfs`), shown in the demo in place of the block (the demo server can't hold the PDF files); a test checks they match.
