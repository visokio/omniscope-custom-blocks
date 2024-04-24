library(omniscope.api)
library(pdftools)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
folderPath = get.option(omni.api, "folderPath")
isRecursive = get.option(omni.api, "recursive")
writeTxt = get.option(omni.api, "writeTxt")

output.data <- data.frame("File" = NULL, "Extracted text" = NULL)

files <- list.files(path=toString(folderPath), pattern="*.pdf", full.names=TRUE, recursive=isRecursive)
lapply(files, function(f) {
    extracted <- tryCatch(
    {
    	# convert
        pdf_text(f)
    }, 
    warning = function(w) {
    	stop(w)
    },
    error = function(e){
        #cannot convert, maybe pwd protected, ignore
        stop(e)
    }
    )
    # write to file if we managed to extract text
    if (!is.null(extracted)) {
        if (writeTxt) {
            txtFileName = paste( sub('\\.pdf$', '', f),"txt", sep=".")
            write.table(extracted, file = txtFileName, sep = "\t", row.names=FALSE, quote=FALSE, col.names=FALSE)
        }
        converted = data.frame("File" = c(basename(f)), "Extracted text" = extracted)
        output.data <<- rbind(output.data, converted)
    }
})

if (!is.null(output.data) && is.data.frame(output.data) && nrow(output.data) > 0 && ncol(output.data) > 0) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)