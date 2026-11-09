# Writes the invented sample PDFs for the PDF Reader block:
#   Rscript sample-data/make-sample-data.R   (from the block folder)
# sample-data/invoices/ holds two one-page supplier invoices and a two-page statement, and a subfolder, archive/,
# with one older invoice (read only when the block's "Include subfolders" option is ticked).

out <- file.path(if (dir.exists("sample-data")) "sample-data" else ".", "invoices")
dir.create(file.path(out, "archive"), recursive = TRUE, showWarnings = FALSE)

# Each page is a character vector of lines, written top to bottom in a plain font.
write_pdf <- function(path, pages) {
  cairo_pdf(path, width = 8.27, height = 11.69, family = "Helvetica", onefile = TRUE)
  on.exit(dev.off())
  for (lines in pages) {
    plot.new()
    par(mar = c(0, 0, 0, 0))
    plot.window(c(0, 1), c(0, 1))
    y <- 0.95
    for (l in lines) {
      text(0.05, y, l, adj = c(0, 1), family = "Helvetica", cex = 1.1)
      y <- y - 0.04
    }
  }
}

write_pdf(file.path(out, "INV-4471 Harbourside Packaging.pdf"), list(c(
  "Harbourside Packaging Ltd",
  "INVOICE",
  "Invoice number: INV-4471",
  "Invoice date: 03/03/2025",
  "Customer: Fernhill Garden Centre",
  "Corrugated boxes, large      200 x 1.85    370.00",
  "Packing tape, 50m              40 x 2.10     84.00",
  "Subtotal: 454.00",
  "VAT 20%: 90.80",
  "Total due: £544.80",
  "Payment terms: 30 days"
)))

write_pdf(file.path(out, "INV-4502 Kestrel Logistics.pdf"), list(c(
  "Kestrel Logistics Midlands Ltd",
  "INVOICE",
  "Invoice number: INV-4502",
  "Invoice date: 10/03/2025",
  "Customer: Fernhill Garden Centre",
  "Pallet delivery, Tamworth to Leeds     3 x 96.00    288.00",
  "Tail-lift surcharge                    3 x 12.50     37.50",
  "Subtotal: 325.50",
  "VAT 20%: 65.10",
  "Total due: £390.60",
  "Payment terms: 14 days"
)))

write_pdf(file.path(out, "Statement March 2025 Pennine Office Supplies.pdf"), list(
  c("Pennine Office Supplies Ltd",
    "STATEMENT OF ACCOUNT",
    "Statement date: 31/03/2025",
    "Customer: Fernhill Garden Centre",
    "Page 1 of 2",
    "Opening balance: 120.00",
    "INV-3310  04/03/2025  Printer paper, 10 reams     62.40",
    "INV-3342  18/03/2025  Toner cartridges, 2          148.80"),
  c("Pennine Office Supplies Ltd",
    "STATEMENT OF ACCOUNT",
    "Page 2 of 2",
    "Payment received 21/03/2025: -120.00",
    "Closing balance: £211.20",
    "Please pay within 30 days.")
))

write_pdf(file.path(out, "archive", "INV-4390 Harbourside Packaging.pdf"), list(c(
  "Harbourside Packaging Ltd",
  "INVOICE",
  "Invoice number: INV-4390",
  "Invoice date: 10/02/2025",
  "Customer: Fernhill Garden Centre",
  "Bubble wrap, 100m roll         10 x 14.00    140.00",
  "Subtotal: 140.00",
  "VAT 20%: 28.00",
  "Total due: £168.00",
  "Payment terms: 30 days"
)))
