library(omniscope.api)
library(survival)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

options.type = get.option(omni.api, "type")
options.time = get.option(omni.api, "time")
options.event = get.option(omni.api, "event")
options.strata = get.option(omni.api, "strata")

is.set <- function(x) !is.null(x) && length(x) == 1 && !is.na(x) && nzchar(x)

if (is.null(input.data)) abort(omni.api, "No input data: connect records with a time and an event field")
if (!is.set(options.time)) abort(omni.api, "Choose the Time field")
if (!is.set(options.event)) abort(omni.api, "Choose the Event field")
has.strata <- is.set(options.strata)

for (f in c(options.time, options.event, if (has.strata) options.strata)) {
  if (!(f %in% names(input.data))) abort(omni.api, paste0("Field not found in the input: ", f))
}

time <- input.data[[options.time]]
if (!is.numeric(time) || inherits(time, c("POSIXct", "Date"))) {
  abort(omni.api, paste0("The Time field must be a number (for example days or months): ", options.time))
}
time <- as.numeric(time)
if (any(time < 0, na.rm = TRUE)) abort(omni.api, paste0("The Time field has negative values: ", options.time))

event <- input.data[[options.event]]
if (is.logical(event)) event <- as.integer(event)
if (!is.numeric(event) || inherits(event, c("POSIXct", "Date"))) {
  abort(omni.api, paste0("The Event field must be 0 / 1, 1 / 2 or true / false: ", options.event))
}
event.values <- unique(event[!is.na(event)])
if (all(event.values %in% c(0, 1))) {
  event <- as.integer(event)
} else if (all(event.values %in% c(1, 2))) {
  event <- as.integer(event == 2)  # 1 = censored, 2 = event, as in R's Surv()
} else {
  abort(omni.api, paste0("The Event field must be 0 / 1 (1 = event), 1 / 2 (2 = event) or true / false; found ",
                         paste(head(sort(event.values), 5), collapse = ", ")))
}

group <- if (has.strata) as.character(input.data[[options.strata]]) else rep("all", nrow(input.data))
group.field <- if (has.strata) options.strata else NULL

# Records with a missing time, event or group are left out, as survfit() would
keep <- !is.na(time) & !is.na(event) & !is.na(group)
d <- data.frame(time = time[keep], event = event[keep], group = group[keep], stringsAsFactors = FALSE)

# Kaplan-Meier: product-limit estimate. Fleming-Harrington: exp(-Nelson-Aalen cumulative hazard)
stype <- if (identical(options.type, "fleming-harrington")) 2 else 1

curve.fields <- c("Time", "At risk", "Events", "Censored", "Survival", "Lower 95%", "Upper 95%",
                  "Std error (log survival)")
summary.fields <- c("Records", "Events", "Censored", "Median time", "Median lower 95%", "Median upper 95%")

empty.frame <- function(fields, group.type = character(0)) {
  df <- as.data.frame(setNames(rep(list(numeric(0)), length(fields)), fields), check.names = FALSE)
  if (!is.null(group.field)) df <- cbind(setNames(data.frame(group.type, stringsAsFactors = FALSE), group.field), df)
  df
}

if (nrow(d) == 0) {
  curve <- empty.frame(curve.fields)
  summary.data <- empty.frame(summary.fields)
} else {
  fit <- survfit(Surv(time, event) ~ group, data = d, stype = stype, ctype = 1)

  groups <- if (is.null(fit$strata)) rep(unique(d$group), length(fit$time)) else
    rep(sub("^group=", "", names(fit$strata)), fit$strata)
  curve <- data.frame(group = groups, time = fit$time, n.risk = as.integer(fit$n.risk),
                      n.event = as.integer(fit$n.event), n.censor = as.integer(fit$n.censor), surv = fit$surv, lower = fit$lower, upper = fit$upper,
                      std.err = fit$std.err, stringsAsFactors = FALSE)

  # A row at time 0 for each group (everyone still in, survival 1), so a step chart starts at 1
  starts <- aggregate(time ~ group, d, length)
  start.rows <- data.frame(group = starts$group, time = 0, n.risk = starts$time, n.event = 0L, n.censor = 0L,
                           surv = 1, lower = 1, upper = 1, std.err = 0, stringsAsFactors = FALSE)
  start.rows <- start.rows[!paste(start.rows$group, 0) %in% paste(curve$group, curve$time), ]
  curve <- rbind(start.rows, curve)
  curve <- curve[order(match(curve$group, unique(groups)), curve$time), ]
  for (n in c("lower", "upper", "std.err")) curve[[n]][!is.finite(curve[[n]])] <- NA
  names(curve) <- c("group", curve.fields)

  table <- summary(fit)$table
  if (is.null(dim(table))) table <- t(as.matrix(table))
  summary.data <- data.frame(group = if (is.null(fit$strata)) unique(d$group) else sub("^group=", "", rownames(table)),
                             as.integer(table[, "records"]), as.integer(table[, "events"]),
                             as.integer(table[, "records"] - table[, "events"]),
                             table[, "median"], table[, "0.95LCL"], table[, "0.95UCL"],
                             stringsAsFactors = FALSE)
  names(summary.data) <- c("group", summary.fields)
  rownames(summary.data) <- NULL
  rownames(curve) <- NULL

  if (has.strata) {
    names(curve)[1] <- group.field
    names(summary.data)[1] <- group.field
  } else {
    curve$group <- NULL
    summary.data$group <- NULL
  }
}

write.output.records(omni.api, curve, output.number=1)
write.output.records(omni.api, summary.data, output.number=2)
close(omni.api)
