library(omniscope.api)
library(data.table)

omni.api = omniscope.api()

# First input: the rename rules (one record per field to rename). Second input: the data to rename.
rules = read.input.records(omni.api, input.number=1)
input.data = read.input.records(omni.api, input.number=2)

if (is.null(rules)) abort(omni.api, "Connect the rename rules (current and new field names) to the first input.")
if (is.null(input.data)) abort(omni.api, "Connect the data whose fields you want to rename to the second input.")

current.names.field = get.option(omni.api, "currentNames")
new.names.field = get.option(omni.api, "newNames")
if (is.null(current.names.field) || current.names.field == "" || !(current.names.field %in% names(rules))) {
  abort(omni.api, "Choose the rules field that holds the current field names (Current field names).")
}
if (is.null(new.names.field) || new.names.field == "" || !(new.names.field %in% names(rules))) {
  abort(omni.api, "Choose the rules field that holds the new field names (New field names).")
}

# Names are compared as text, with spaces at either end removed.
as.name.text = function(x) {
  x = trimws(as.character(x))
  x[!is.na(x) & x == ""] = NA
  x
}
current.names = as.name.text(rules[[current.names.field]])
new.names = as.name.text(rules[[new.names.field]])

# A rule with no current name renames nothing: skip it. A rule with a current name but no new name is a mistake.
keep = !is.na(current.names)
current.names = current.names[keep]
new.names = new.names[keep]

if (any(is.na(new.names))) {
  abort(omni.api, paste0("These rules have no new name: ", paste(unique(current.names[is.na(new.names)]), collapse=", ")))
}
if (anyDuplicated(current.names)) {
  abort(omni.api, paste0("The current field names contain duplicates: ",
                         paste(unique(current.names[duplicated(current.names)]), collapse=", ")))
}

old.names = names(input.data)
used = current.names %in% old.names

unused.rules = data.frame(current.names[!used], new.names[!used], stringsAsFactors=FALSE)
names(unused.rules) = c("Current Name", "New Name")
unchanged.fields = data.frame(Field = setdiff(old.names, current.names[used]), stringsAsFactors=FALSE)

result.names = old.names
result.names[match(current.names[used], old.names)] = new.names[used]
if (anyDuplicated(result.names)) {
  abort(omni.api, paste0("Renaming would give two fields the same name: ",
                         paste(unique(result.names[duplicated(result.names)]), collapse=", ")))
}

output.data = as.data.table(input.data)
setnames(output.data, result.names)

write.output.records(omni.api, output.data, output.number=1)
write.output.records(omni.api, unused.rules, output.number=2)
write.output.records(omni.api, unchanged.fields, output.number=3)
close(omni.api)
