# Stand-in for Omniscope's R API (the omniscope.api package), for running an R block's script.R outside
# Omniscope. It mirrors tools/python/harness: inputs come from data frames or CSV files, options from a list
# (manifest defaults fill the gaps), outputs are captured as data frames, and commit / close / cancel / abort
# and messages are recorded.
#
#   source("tools/r/harness.R")
#   res <- run_block("Preparation/Join/Fuzzy-Join", list(left_df, right_df), list(left = "Name", right = "Name"))
#   res$status        # "committed" / "cancelled" / "aborted" / NA
#   res$outputs[[1]]  # data frame written to the first output
#   res$messages; res$final_message; res$error
#
# The real package is installed by Omniscope and is not on CRAN; this follows its published reference
# (read.input.records, write.output.records, write.output, get.option, update.message, commit, close, cancel,
# abort, is.docker). Input and output numbers are one-based, as in R.
#
# Behaviour that matters for tests:
# * abort() ends the script at once; cancel() does not.
# * after commit / close / cancel / abort the API cannot be used again.
# * an option the manifest does not declare is an error (catches typos in tests and scripts).
# * the field names and broad types written to one output must not change between writes.
# * text arrives as character (not factor), missing and empty text as NA; whole numbers as integer;
#   dates as POSIXct in UTC; a second input that is not connected as NULL.

suppressPackageStartupMessages(library(jsonlite))

omniscope_abort_condition <- function(message) {
  structure(class = c("omniscope_abort", "condition"), list(message = message, call = NULL))
}

.omniscope_broad_type <- function(x) {
  if (is.logical(x)) return("BOOLEAN")
  if (inherits(x, c("POSIXct", "Date"))) return("DATE")
  if (is.integer(x) || is.double(x)) return("NUMBER")  # Integer and Decimal widen into each other
  "TEXT"
}

# Give a data frame the types a block receives from Omniscope.
omniscope_types <- function(df) {
  df <- as.data.frame(df, stringsAsFactors = FALSE, check.names = FALSE)
  for (n in names(df)) {
    x <- df[[n]]
    if (is.factor(x)) x <- as.character(x)
    if (is.character(x)) {
      x[!is.na(x) & x == ""] <- NA  # empty text and missing are the same once through Omniscope
      nn <- x[!is.na(x)]
      if (length(nn) && all(grepl("^\\d{4}-\\d{2}-\\d{2}([ T]\\d{2}:\\d{2}(:\\d{2})?)?$", nn))) {
        x <- as.POSIXct(x, tz = "UTC", tryFormats = c("%Y-%m-%d %H:%M:%OS", "%Y-%m-%dT%H:%M:%OS",
                                                       "%Y-%m-%d %H:%M", "%Y-%m-%d"))
      }
    } else if (is.double(x) && !inherits(x, c("POSIXct", "Date"))) {
      nn <- x[!is.na(x)]
      if (length(nn) && all(nn == round(nn)) && all(abs(nn) < .Machine$integer.max)) x <- as.integer(x)
    } else if (inherits(x, "Date")) {
      x <- as.POSIXct(format(x), tz = "UTC")
    }
    df[[n]] <- x
  }
  df
}

.omniscope_read_source <- function(src) {
  if (is.null(src)) return(NULL)
  if (is.character(src) && length(src) == 1) {
    src <- utils::read.csv(src, stringsAsFactors = FALSE, check.names = FALSE, na.strings = c("", "NA"))
  }
  omniscope_types(src)
}

# Build the API functions over one execution's state. Returned as an environment the script runs in.
.omniscope_api_env <- function(state, parent) {
  env <- new.env(parent = parent)

  check_open <- function() {
    if (!is.na(state$status)) stop("Omniscope API used after the execution was ", state$status, call. = FALSE)
  }
  finish <- function(status, message) {
    check_open()
    state$status <- status
    state$final_message <- if (is.null(message)) "" else as.character(message)
  }
  append_output <- function(data, idx) {
    if (!is.data.frame(data)) stop("output data must be a data.frame, got ", class(data)[1], call. = FALSE)
    nms <- names(data)
    if (anyDuplicated(nms)) stop("duplicate output field names: ", paste(nms, collapse = ", "), call. = FALSE)
    if (any(trimws(nms) == "")) stop("empty output field name", call. = FALSE)
    schema <- vapply(data, .omniscope_broad_type, "")
    key <- as.character(idx)
    if (!is.null(state$schemas[[key]]) && !identical(state$schemas[[key]], schema)) {
      stop("output ", idx, " schema changed between writes", call. = FALSE)
    }
    state$schemas[[key]] <- schema
    state$outputs[[key]] <- c(state$outputs[[key]], list(data))
  }
  resolve_output <- function(output) {
    if (is.character(output)) {
      i <- match(output, state$output_ids)
      if (is.na(i)) stop("unknown output name '", output, "'", call. = FALSE)
      return(i)
    }
    as.integer(output)
  }

  env$omniscope.api <- function() {
    if (state$created) stop("only one omniscope.api() instance is allowed per execution", call. = FALSE)
    state$created <- TRUE
    structure(list(), class = "OmniscopeApi")
  }
  env$read.input.records <- function(omni.api, input.number = 1) {
    check_open()
    if (input.number > length(state$inputs)) return(NULL)
    .omniscope_read_source(state$inputs[[input.number]])
  }
  env$get.option <- function(omni.api, option.name) {
    check_open()
    key <- tolower(option.name)
    if (!is.null(state$declared) && !(key %in% state$declared)) {
      stop("option '", option.name, "' is not declared in the block's manifest", call. = FALSE)
    }
    names(state$options) <- tolower(names(state$options))
    state$options[[key]]
  }
  env$is.docker <- function(omni.api) FALSE
  env$update.message <- function(omni.api, message) {
    check_open()
    state$messages <- c(state$messages, as.character(message))
    invisible(NULL)
  }
  env$write.output.records <- function(omni.api, output.data, output.number = 1) {
    check_open()
    append_output(output.data, as.integer(output.number))
  }
  env$write.output <- function(omni.api, output.data, output) {
    check_open()
    append_output(output.data, resolve_output(output))
  }
  env$commit <- function(omni.api, message = "") finish("committed", message)
  env$close <- function(con, message = "", ...) {
    if (!inherits(con, "OmniscopeApi")) return(base::close(con, ...))
    finish("committed", message)
  }
  env$cancel <- function(omni.api, message = "") finish("cancelled", message)
  env$abort <- function(omni.api, message = "") {
    finish("aborted", message)
    stop(omniscope_abort_condition(state$final_message))
  }
  # library(omniscope.api) loads this stand-in; every other package loads as normal
  env$library <- function(package, ...) {
    name <- as.character(substitute(package))
    if (identical(name, "omniscope.api")) return(invisible(NULL))
    base::library(name, character.only = TRUE, ...)
  }
  env
}

run_block <- function(block_dir, inputs = list(), options = list(), strict_options = TRUE, script = NULL) {
  manifest_path <- file.path(block_dir, "manifest.json")
  manifest <- if (file.exists(manifest_path)) jsonlite::fromJSON(manifest_path, simplifyVector = FALSE) else NULL

  defaults <- list()
  declared <- NULL
  if (!is.null(manifest)) {
    declared <- character(0)
    for (o in manifest$options) {
      declared <- c(declared, tolower(o$name))
      value <- o$defaultValue
      if (is.null(value) && grepl("BooleanCustomBlockPublicOption$", o[["@visokiotype"]])) value <- FALSE
      if (!is.null(value)) defaults[[o$name]] <- if (is.list(value)) unlist(value) else value
    }
  }
  for (k in names(options)) {
    if (strict_options && !is.null(declared) && !(tolower(k) %in% declared)) {
      stop("option '", k, "' is not declared in manifest.json")
    }
  }
  opts <- defaults
  for (k in names(options)) opts[k] <- list(options[[k]])

  if (is.data.frame(inputs) || is.character(inputs)) inputs <- list(inputs)

  state <- new.env()
  state$inputs <- inputs
  state$options <- opts
  state$declared <- declared
  state$output_ids <- vapply(manifest$blockOutputs, function(o) o$id, "")
  state$outputs <- list()
  state$schemas <- list()
  state$messages <- character(0)
  state$status <- NA_character_
  state$final_message <- NA_character_
  state$created <- FALSE

  if (is.null(script)) {
    script <- file.path(block_dir, if (is.null(manifest$scriptFilename)) "script.R" else manifest$scriptFilename)
  }
  script_env <- .omniscope_api_env(state, globalenv())
  error <- NULL
  tryCatch(
    sys.source(script, envir = script_env, keep.source = FALSE),
    omniscope_abort = function(c) NULL,
    error = function(e) error <<- e
  )

  outputs <- list()
  for (key in names(state$outputs)) {
    frames <- state$outputs[[key]]
    outputs[[as.integer(key)]] <- if (length(frames) == 1) frames[[1]] else do.call(rbind, frames)
  }
  structure(list(status = state$status, outputs = outputs, messages = state$messages,
                 final_message = state$final_message, error = error), class = "omniscope_block_result")
}

# Fails the calling test with the block's error or final message unless the block committed.
expect_committed <- function(res) {
  if (!is.null(res$error)) stop("block raised: ", conditionMessage(res$error), call. = FALSE)
  if (!identical(res$status, "committed")) {
    stop("block finished with status ", res$status, ": ", res$final_message, call. = FALSE)
  }
  invisible(res)
}
