library(omniscope.api)
library(data.table)
omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
path.field = get.option(omni.api, "pathField")
folder = get.option(omni.api, "folder")
recursive = get.option(omni.api, "recursive")
scan.first = get.option(omni.api, "scanFirst")
action.additional.fields = get.option(omni.api, "actionAdditionalFields")
action.missing.fields = get.option(omni.api, "actionMissingFields")
action.incorrect.type = get.option(omni.api, "actionIncorrectFieldType")
add.source.field = get.option(omni.api, "addSourceField")
source.field.name = get.option(omni.api, "sourceFieldName")

should.coerce = function(action) {
	if (action == "WARN") return (TRUE)
    else if (action == "IGNORE") return (TRUE)
    return (FALSE)
}

should.warn = function(action) {
	if (action == "WARN") return (TRUE)
    return (FALSE)
}

should.stop = function(action) {
	if (action == "ERROR") return (TRUE)
    return (FALSE)
}


    



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

read.rds = function(file.list, schema) {
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
      if (should.coerce(action.missing.fields)) {
        for (missing.field in missing.field.names) {
          na.value = coerce.type(field.types[[missing.field]], NA)
          df[, (missing.field) := na.value]
        }
        
      } 
      
      if(should.warn(action.missing.fields)) {
      	updateMessage(omni.api, paste(f,"is missing fields:", paste(missing.field.names, collapse = ", "), sep=" "))
      } else if(should.stop(action.missing.fields)) {
        abort(omni.api, paste(f,"is missing fields:", paste(missing.field.names, collapse = ", "), sep=" "))
      }
    }
    
    if (length(new.field.names) > 0) {
      if (should.coerce(action.additional.fields)) {
        df = df[, field.names, with=FALSE]
      } 
      if(should.warn(action.additional.fields)) {
      	updateMessage(omni.api, paste(f,"has additional fields:", paste(new.field.names, collapse = ", "), sep=" "))
      } else if(should.stop(action.additional.fields)) {
        abort(omni.api, paste(f,"has additional fields:", paste(new.field.names, collapse = ", "), sep=" "))
      }
    }
    
	current.field.types = sapply(names(df), function(x) {get.type.str(df[[x]])})
    if (!all(field.types == current.field.types)) {
      for (current.field in names(df)) {
        if (field.types[[current.field]] != current.field.types[[current.field]]) {
          if (should.coerce(action.incorrect.type)) {
            coerced.col = coerce.type(field.types[[current.field]], df[[current.field]])
            df[, (current.field) := coerced.col]
          } 
          if(should.warn(action.incorrect.type)) {
      		updateMessage(omni.api, paste(f,"schemas don't match. Reference:", paste(field.types, collapse = ", "), " Current:", paste(current.field.types, collapse = ", "), sep=" "))
          } else if(should.stop(action.incorrect.type)) {
            abort(omni.api, paste(f,"schemas don't match. Reference:", paste(field.types, collapse = ", "), " Current:", paste(current.field.types, collapse = ", "), sep=" "))
          }
        }
      }    
    }
    
    setcolorder(df, field.names)
    
    if (add.source.field) {
		df[, (source.field.name) := f]
	}

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


read.rds(file.list, schema)


close(omni.api)