library(omniscope.api)
library(tools)

omni.api = omniscope.api()

rda.file.option = get.option(omni.api, "rda_file")
obj.to.load.option = get.option(omni.api, "obj")

load.file.rdata = function(filename, obj.to.load) {
	env = new.env()
	load(rda.file.option, envir = env)
    objs = names(env)
    if (length(objs) == 0) abort(omni.api, "Your file contains no objects to load")
    if (is.null(obj.to.load)) obj.to.load = objs[1]

    if (!(obj.to.load %in% objs)) {
    	objs.collapsed = paste(objs, collapse=", ")
    	abort(omni.api, paste("The file does not contain an object name ", obj.to.load, ". Available objects are: ", objs.collapsed, sep=""))
	}

    list(data = as.data.frame(get(obj.to.load, envir=env)), objs = data.frame(Objects = objs))
}

load.file.rds = function(filename) {
    list(data = as.data.frame(readRDS(filename)), objs = NULL)
}

load.file = function(filename, obj.to.load) {
	ext = tolower(file_ext(filename))
	if (ext == "rds") {
    	return(load.file.rds(filename))
	} else if (ext == "rda" || ext == "rdata") {
    	return(load.file.rdata(filename, obj.to.load))
    } else {
    	abort(omni.api, "Unsupported file type")
        return(NULL)
    }
}


result = tryCatch(
  load.file(rda.file.option, obj.to.load.option),
  error = function(e) {abort(omni.api, "Invalid R data file")}
)

output.data.1 = result$data
output.data.2 = result$objs

if (!is.null(output.data.1)) {
  write.output.records(omni.api, output.data.1, output.number=1)
}
if (!is.null(output.data.2)) {
  write.output.records(omni.api, output.data.2, output.number=2)
}

close(omni.api)
