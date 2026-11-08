"""Writes the invented sample PDFs in sample-data/pdfs/ and the list of them, sample-data/report-sections.csv.

The PDFs are a fictional company's monthly board pack, one file per section, with a line of text on each page.
Needs only the Python standard library:

    python3 sample-data/make_sample_pdfs.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
    ("01-cover.pdf", "Cover", ["Harbour Lane Foods - Board pack, March 2025"]),
    ("02-trading-summary.pdf", "Trading summary", ["Trading summary: sales by region", "Trading summary: margin by product line"]),
    ("03-cash-flow.pdf", "Cash flow", ["Cash flow: thirteen-week forecast"]),
    ("04-risks.pdf", "Risks and actions", ["Risks and actions: supplier delays", "Risks and actions: energy costs",
                                           "Risks and actions: open actions"]),
    ("05-appendix.pdf", "", ["Appendix: definitions"]),
]


def write_pdf(path, lines):
    """A minimal PDF, one A4 page per line of text (Helvetica 18 pt)."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for line in lines:
        text = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 18 Tf 60 760 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as fh:
        fh.write(out)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "pdfs"), exist_ok=True)
    for name, _, lines in SECTIONS:
        write_pdf(os.path.join(HERE, "pdfs", name), lines)
    with open(os.path.join(HERE, "report-sections.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Section", "File name", "Bookmark"])
        for k, (name, title, _) in enumerate(SECTIONS, start=1):
            w.writerow([k, name, title])
    print(len(SECTIONS), "PDFs written")
