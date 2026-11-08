library(omniscope.api)
library(pdftools)

omni.api = omniscope.api()

folder.path = get.option(omni.api, "folderPath")
is.recursive = isTRUE(get.option(omni.api, "recursive"))
write.txt = isTRUE(get.option(omni.api, "writeTxt"))

if (is.null(folder.path) || length(folder.path) == 0 || is.na(folder.path[1]) || trimws(folder.path[1]) == "") {
  abort(omni.api, "Choose a folder of PDF files (or one PDF file) in \"Folder path\".")
}
folder.path = as.character(folder.path)

# The option may name a folder, or a single PDF file.
if (dir.exists(folder.path)) {
  files = list.files(path = folder.path, pattern = "\\.pdf$", ignore.case = TRUE, full.names = TRUE,
                     recursive = is.recursive)
  files = sort(files)
  base = normalizePath(folder.path, winslash = "/")
} else if (file.exists(folder.path)) {
  if (!grepl("\\.pdf$", folder.path, ignore.case = TRUE)) abort(omni.api, paste0("Not a PDF file: ", folder.path))
  files = folder.path
  base = normalizePath(dirname(folder.path), winslash = "/")
} else {
  abort(omni.api, paste0("Folder not found: ", folder.path))
}

# File names relative to the chosen folder, so files of the same name in different subfolders stay apart.
relative.name = function(f) {
  full = normalizePath(f, winslash = "/")
  if (startsWith(full, paste0(base, "/"))) substring(full, nchar(base) + 2) else basename(f)
}

pages.list = list()
skipped = character(0)
files.read = 0
for (f in files) {
  pages = tryCatch(
    suppressMessages(withCallingHandlers(pdf_text(f), warning = function(w) invokeRestart("muffleWarning"))),
    error = function(e) e
  )
  if (inherits(pages, "error")) {
    # damaged, or protected with a password
    skipped = c(skipped, paste0(relative.name(f), " (", conditionMessage(pages), ")"))
    next
  }
  files.read = files.read + 1
  if (write.txt) {
    txt.file = sub("\\.pdf$", ".txt", f, ignore.case = TRUE)
    ok = tryCatch({ writeLines(pages, txt.file); TRUE }, error = function(e) FALSE,
                  warning = function(w) FALSE)
    if (!ok) skipped = c(skipped, paste0(relative.name(f), " (text read, but ", basename(txt.file), " could not be written)"))
  }
  if (length(pages) == 0) next
  pages.list[[length(pages.list) + 1]] = data.frame(
    "File" = relative.name(f),
    "Page" = seq_along(pages),
    "Pages" = length(pages),
    "Extracted text" = pages,
    check.names = FALSE, stringsAsFactors = FALSE
  )
}

output.data = if (length(pages.list) > 0) do.call(rbind, pages.list) else
  data.frame("File" = character(0), "Page" = integer(0), "Pages" = integer(0), "Extracted text" = character(0),
             check.names = FALSE, stringsAsFactors = FALSE)

write.output.records(omni.api, output.data, output.number = 1)

message = paste0(files.read, " PDF file", if (files.read != 1) "s" else "", ", ", nrow(output.data), " page",
                 if (nrow(output.data) != 1) "s" else "", ".")
if (length(files) == 0) message = paste0("No PDF files found", if (!is.recursive) " (tick Include subfolders to search them)" else "", ".")
if (length(skipped) > 0) {
  message = paste0(message, " Skipped: ", paste(head(skipped, 5), collapse = "; "),
                   if (length(skipped) > 5) paste0("; and ", length(skipped) - 5, " more") else "")
  update.message(omni.api, message)
}
close(omni.api, message)
