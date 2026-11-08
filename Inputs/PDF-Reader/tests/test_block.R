# Unit tests for the PDF Reader block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Inputs/PDF-Reader
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).
# Needs the pdftools package. tests/fixtures/protected.pdf is the Kestrel sample invoice encrypted with the
# password "letmein" (made with pypdf).

invoices <- file.path(BLOCK_DIR, "sample-data", "invoices")
protected <- file.path(BLOCK_DIR, "tests", "fixtures", "protected.pdf")

run <- function(...) suppressMessages(run_block(BLOCK_DIR, list(), list(...)))

# A copy of the sample folder (and anything else) in a fresh temporary folder.
copy_invoices <- function() {
  dir <- tempfile("pdfs-")
  dir.create(dir)
  file.copy(list.files(invoices, full.names = TRUE), dir, recursive = TRUE)
  dir
}

blank_pdf <- function(path, pages = 1, text = NULL) {
  grDevices::cairo_pdf(path, onefile = TRUE)
  for (i in seq_len(pages)) {
    plot.new()
    if (!is.null(text)) text(0.5, 0.5, sprintf(text, i))
  }
  grDevices::dev.off()
}

test_that("the sample folder gives one record per page, with file, page number and text", {
  res <- expect_committed(run(folderPath = invoices))
  out <- res$outputs[[1]]
  expect_equal(names(out), c("File", "Page", "Pages", "Extracted text"))
  expect_equal(nrow(out), 4)
  expect_equal(out$File, c("INV-4471 Harbourside Packaging.pdf", "INV-4502 Kestrel Logistics.pdf",
                           rep("Statement March 2025 Pennine Office Supplies.pdf", 2)))
  expect_equal(out$Page, c(1L, 1L, 1L, 2L))
  expect_equal(out$Pages, c(1L, 1L, 2L, 2L))
  expect_match(out$`Extracted text`[1], "Invoice number: INV-4471")
  expect_match(out$`Extracted text`[1], "Total due: £544.80", fixed = TRUE)
  expect_match(out$`Extracted text`[4], "Closing balance: £211.20", fixed = TRUE)
  expect_equal(res$final_message, "3 PDF files, 4 pages.")
})

test_that("subfolders are read only when asked, with the path from the chosen folder", {
  out <- expect_committed(run(folderPath = invoices, recursive = TRUE))$outputs[[1]]
  expect_equal(nrow(out), 5)
  expect_equal(out$File[1], "archive/INV-4390 Harbourside Packaging.pdf")
})

test_that("a single PDF file can be chosen instead of a folder", {
  out <- expect_committed(run(folderPath = file.path(invoices, "INV-4502 Kestrel Logistics.pdf")))$outputs[[1]]
  expect_equal(nrow(out), 1)
  expect_equal(out$File, "INV-4502 Kestrel Logistics.pdf")
})

test_that("only files ending in .pdf are read, in any case", {
  dir <- tempfile("pdfs-"); dir.create(dir)
  blank_pdf(file.path(dir, "UPPER.PDF"), text = "Upper case %d")
  writeLines("not a pdf", file.path(dir, "readme-pdf.txt"))
  res <- expect_committed(run(folderPath = dir))
  expect_equal(res$outputs[[1]]$File, "UPPER.PDF")
  expect_match(res$outputs[[1]]$`Extracted text`, "Upper case 1")
})

test_that("a damaged or password-protected PDF is skipped and named; the others are read", {
  dir <- copy_invoices()
  writeLines("%PDF-1.4 this is not really a PDF", file.path(dir, "broken.pdf"))
  file.copy(protected, file.path(dir, "protected.pdf"))
  res <- expect_committed(run(folderPath = dir))
  expect_equal(nrow(res$outputs[[1]]), 4)
  expect_match(res$final_message, "^3 PDF files, 4 pages. Skipped: broken.pdf \\(.*\\); protected.pdf \\(")
  expect_true(length(res$messages) > 0)
})

test_that("pages without text (scanned images) give records with empty text", {
  dir <- tempfile("pdfs-"); dir.create(dir)
  blank_pdf(file.path(dir, "scan.pdf"), pages = 2)
  out <- expect_committed(run(folderPath = dir))$outputs[[1]]
  expect_equal(out$Page, 1:2)
  expect_true(all(trimws(out$`Extracted text`) == ""))
})

test_that("Extract to TXT files writes the text beside each PDF", {
  dir <- copy_invoices()
  expect_committed(run(folderPath = dir, writeTxt = TRUE))
  txt <- file.path(dir, "Statement March 2025 Pennine Office Supplies.txt")
  expect_true(file.exists(txt))
  lines <- readLines(txt, encoding = "UTF-8")
  expect_true(any(grepl("Opening balance: 120.00", lines)))
  expect_true(any(grepl("Closing balance", lines)))
})

test_that("a folder that can't be written to still gives the text, with a note", {
  skip_if(Sys.info()[["user"]] == "root", "root can write anywhere")
  dir <- copy_invoices()
  Sys.chmod(dir, "555")
  on.exit(Sys.chmod(dir, "755"))
  res <- expect_committed(run(folderPath = dir, writeTxt = TRUE))
  expect_equal(nrow(res$outputs[[1]]), 4)
  expect_match(res$final_message, "could not be written")
})

test_that("an empty folder gives an empty output with the fields", {
  dir <- tempfile("pdfs-"); dir.create(dir)
  res <- expect_committed(run(folderPath = dir))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("File", "Page", "Pages", "Extracted text"))
  expect_match(res$final_message, "No PDF files found")
})

test_that("a missing folder, no folder or a file that is not a PDF stops with a message", {
  res <- run(folderPath = file.path(tempdir(), "no-such-folder"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Folder not found")
  res <- run_block(BLOCK_DIR, list(), list())
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose a folder")
  csv <- tempfile(fileext = ".csv"); writeLines("a", csv)
  res <- run(folderPath = csv)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Not a PDF file")
})

test_that("a 300-page PDF is read in seconds", {
  dir <- tempfile("pdfs-"); dir.create(dir)
  blank_pdf(file.path(dir, "long.pdf"), pages = 300, text = "Page text %d")
  t <- system.time(res <- run(folderPath = dir))
  out <- expect_committed(res)$outputs[[1]]
  expect_equal(nrow(out), 300)
  expect_match(out$`Extracted text`[300], "Page text 300")
  expect_lt(t[["elapsed"]], 30)
})


test_that("placeholder.csv is the block's output for the sample", {
  # The demo shows sample-data/placeholder.csv in place of the block's Text output: it must stay identical.
  out <- expect_committed(run(folderPath = invoices, recursive = FALSE, writeTxt = FALSE))$outputs[[1]]
  as_text <- function(x) {
    if (inherits(x, "POSIXct")) x <- format(x, "%Y-%m-%d", tz = "UTC")
    if (is.logical(x)) x <- ifelse(x, "true", "false")
    x <- as.character(x)
    ifelse(is.na(x), "", x)
  }
  placeholder <- utils::read.csv(file.path(BLOCK_DIR, "sample-data", "placeholder.csv"), colClasses = "character",
                                 check.names = FALSE, na.strings = character(0), encoding = "UTF-8")
  expect_equal(names(placeholder), names(out))
  for (n in names(out)) expect_equal(placeholder[[n]], as_text(out[[n]]), info = n)
})
