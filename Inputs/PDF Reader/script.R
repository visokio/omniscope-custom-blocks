library(omniscope)
library(pdftools)

omniscope = Omniscope()

input.data = read.input.records(omniscope, input.number=1)
folderPath = get.option(omniscope, "folderPath")
isRecursive = get.option(omniscope, "recursive")
writeTxt = get.option(omniscope, "writeTxt")

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


if (!is.null(output.data)) {
  write.output.records(omniscope, output.data, output.number=1)
}
close(omniscope)
