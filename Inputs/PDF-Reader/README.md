# PDF Reader

Extracts the text of every PDF file in a folder, one record per page, with the file name and page number. Optionally writes a .txt file beside each PDF.

Invoices, statements, reports and letters often arrive as PDF files in a shared folder. This block reads the text layer of each one so the text can be searched, counted or picked apart in a workflow.

- **Which files**: every file in the chosen folder whose name ends in `.pdf` (any case), in name order; with **Include subfolders**, those in subfolders too. The option can also name a single PDF file.
- **One record per page**: *File* (the name, or the path from the chosen folder for files in subfolders), *Page* (1, 2, ...), *Pages* (the number of pages in that file) and *Extracted text*.
- **The text** is laid out as on the page, with spaces keeping columns roughly aligned and line breaks between lines.
- **Files that can't be read**, such as damaged files or files protected with a password, are skipped; the block's message names them (up to five) and the rest are read.
- **Extract to TXT files** also saves each PDF's text in a .txt file of the same name beside it (`Invoice 12.pdf` gives `Invoice 12.txt`, replacing any file of that name). If the folder can't be written to, the text is still output and the message says so.

## Language and libraries

R, with the pdftools package (MIT licence), which uses the Poppler PDF library (GPL). pdftools must be installed on the Omniscope server's R (`install.packages("pdftools")`); on Linux it needs Poppler's C++ library first (`libpoppler-cpp-dev` on Debian and Ubuntu, which the block's Docker settings list).

## Inputs

None. The block is a source: it reads the folder chosen in its options.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Folder path | `folderPath` | File | The folder of PDF files to read, on the Omniscope server, or a single PDF file. |
| Include subfolders | `recursive` | Yes/no | Also read PDF files in subfolders. Default: no. |
| Extract to TXT files | `writeTxt` | Yes/no | Also save each PDF's text as a .txt file beside it. Default: no. |

## Outputs

- **Text** (`Output Data`): one record per page: File, Page, Pages, Extracted text. An empty folder gives no records (the fields are still there) and the message "No PDF files found".

## Limits

- **No OCR**: scanned documents that are only pictures of text give pages with empty text.
- The text comes out in reading order as Poppler lays it out; tables become lines of text with spaces between the columns, not fields. Pick values out with formulas (for example a regular expression for "Total due").
- Every file is read in full on each run. In tests, a 300-page PDF was read in under a second.
- The folder must be one the Omniscope server can read; a folder on your own computer is not visible to a server elsewhere.

## Source

[script.R](script.R)

`sample-data/invoices/` holds three invented PDF documents (two one-page invoices and a two-page statement) and, in `archive/`, one older invoice. They are written by `sample-data/make-sample-data.R`. `sample-data/placeholder.csv` is the block's Text output for the folder (without subfolders), shown in the demo in place of the block (the demo server can't hold the PDF files); a test checks they match.
