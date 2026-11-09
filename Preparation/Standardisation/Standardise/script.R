# Standardise: rescales each chosen number field to the range 0 to 1 (min-max scaling):
# new value = (value - lowest) / (highest - lowest). Missing values stay missing and are ignored when finding the
# lowest and highest; a field whose values are all the same becomes 0.
library(omniscope.api)
library(data.table)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
fields = get.option(omni.api, "fields")

if (is.null(input.data)) {
  abort(omni.api, "Connect the records to standardise to the block's input.")
}
if (length(fields) == 0) {
  abort(omni.api, "Choose at least one field to standardise.")
}

missing.fields = setdiff(fields, names(input.data))
if (length(missing.fields) > 0) {
  abort(omni.api, paste0("Not in the input: ", paste(missing.fields, collapse = ", "), "."))
}
not.numbers = fields[!vapply(fields, function(f) is.numeric(input.data[[f]]), logical(1))]
if (length(not.numbers) > 0) {
  abort(omni.api, paste0("Only number fields can be standardised; not: ", paste(not.numbers, collapse = ", "), "."))
}

setDT(input.data)

constant.fields = character(0)
for (field in fields) {
  values = as.numeric(input.data[[field]])
  present = values[is.finite(values)]
  if (length(present) == 0) {
    scaled = rep(NA_real_, length(values))
  } else {
    field.min = min(present)
    field.max = max(present)
    if (field.max == field.min) {
      constant.fields = c(constant.fields, field)
      scaled = ifelse(is.na(values), NA_real_, 0)
    } else {
      scaled = (values - field.min) / (field.max - field.min)
    }
  }
  input.data[, (field) := scaled]
}

if (length(constant.fields) > 0) {
  update.message(omni.api, paste0("All values the same, so set to 0: ", paste(constant.fields, collapse = ", "), "."))
}

write.output.records(omni.api, input.data, output.number=1)
close(omni.api)
