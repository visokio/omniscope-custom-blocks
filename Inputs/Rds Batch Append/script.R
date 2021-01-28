library(omniscope.api)
library(data.table)
omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
path.field = get.option(omni.api, "pathField")
folder = get.option(omni.api, "folder")
recursive = get.option(omni.api, "recursive")
scan.first = get.option(omni.api, "scanFirst")
coerce = get.option(omni.api, "coerce")



if (!is.null(input.data)) setDT(input.data)

get.file.paths.from.folder = function(folder, recursive) {

  list.files(folder, pattern = "*.rds", recursive = recursive, full.names = TRUE)
  
}

get.file.paths.from.input = function(input.data, field) {
  as.character(input.data[[field]])
}

get.type.str = function(col) {
  int.types = c("integer")
  float.types = c("double", "numeric")
  date.types = c("POSIXct", "POSIXlt", "POSIXt", "Date")
  text.types = c("character", "factor")
  
  if (is.type.in(col, int.types)) return("int")
  if (is.type.in(col, float.types)) return("float")
  if (is.type.in(col, date.types)) return("datetime")
  if (is.type.in(col, text.types)) return("text")
  return(NULL)
}

coerce.type = function(t, col) {
  if (t == "int") return(as.integer(col))
  if (t == "float") return(as.numeric(col))
  if (t == "datetime") return(as.Date(col))
  if (t == "text") return(as.character(col))
  return(col)
}

is.type.in = function(col, types) {
  for(t in types) {
    if (inherits(col, t)) {
      return(TRUE)
    }
  }
  return(FALSE)
}


get.schema = function(file.list) {
  field.names = as.character(c())
  field.types = as.character(c())
  for (f in file.list) {
    df = as.data.table(readRDS(f))
    new.field.names = setdiff(names(df), field.names)
    
    if (length(new.field.names) > 0) {
      field.names = c(field.names, new.field.names)
      new.field.types = sapply(new.field.names, function(x) {get.type.str(df[[x]])})
      field.types = c(field.types, new.field.types)
    }
  }
  list(field.names=field.names, field.types=field.types)
}

read.rds = function(file.list, schema, coerce) {
  field.names = as.character(c())
  field.types = as.character(c())
  if (!is.null(schema)) {
    field.names = schema$field.names
    field.types = schema$field.types
  }
  
  for (f in file.list) {
    df = as.data.table(readRDS(f))
    new.field.names = setdiff(names(df), field.names)
    missing.field.names = setdiff(field.names, names(df))
    
    if (length(field.names) == 0) {
      field.names = new.field.names
      field.types = sapply(new.field.names, function(x) {get.type.str(df[[x]])})
      new.field.names = c()
    }
    
    if (length(missing.field.names) > 0) {
      if (coerce) {
        for (missing.field in missing.field.names) {
          na.value = coerce.type(field.types[[missing.field]], NA)
          df[, (missing.field) := na.value]
        }
        
      } else {
        abort(omni.api, paste(f,"is missing fields:", paste(missing.field.names, collapse = ", "), sep=" "))
      }
    }
    
    if (length(new.field.names) > 0) {
      if (coerce) {
        df = df[, field.names, with=FALSE]
      } else {
        abort(omni.api, paste(f,"has extraneous fields:", paste(new.field.names, collapse = ", "), sep=" "))
      }
    }
    
	current.field.types = sapply(names(df), function(x) {get.type.str(df[[x]])})
    if (!all(field.types == current.field.types)) {
      for (current.field in names(df)) {
        if (field.types[[current.field]] != current.field.types[[current.field]]) {
          if (coerce) {
            coerced.col = coerce.type(field.types[[current.field]], df[[current.field]])
            df[, (current.field) := coerced.col]
          } else {
            abort(omni.api, paste(f,"schemas don't match. Reference:", paste(field.types, collapse = ", "), " Current:", paste(current.field.types, collapse = ", "), sep=" "))
          }
        }
      }    
    }
    
    setcolorder(df, field.names)

    write.output.records(omni.api, df, output.number=1)
    
    
  }

}

file.list = c()
if (!is.null(input.data)) {
	if (is.null(path.field)) abort(omni.api, "input data is connected, but path field is not specified")
	file.list = get.file.paths.from.input(input.data, path.field)
} else {
	if (is.null(folder)) abort(omni.api, "neither input data nor a folder is specified")
    file.list = get.file.paths.from.folder(folder, recursive)
}

schema = NULL
if (scan.first) schema = get.schema(file.list)


read.rds(file.list, schema, coerce)


close(omni.api)