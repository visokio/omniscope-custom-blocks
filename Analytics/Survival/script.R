library(omniscope.api)
library(survival)
library(ggfortify)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

options.type = get.option(omni.api, "type")
options.time = get.option(omni.api, "time")
options.event = get.option(omni.api, "event")
options.strata = get.option(omni.api, "strata")

if (!is.null(options.strata)) {
  km_fit <- survfit(Surv(input.data[,options.time], input.data[,options.event]) ~ input.data[[options.strata]], data=input.data, type=options.type)
} else {
  km_fit <- survfit(formula = Surv(input.data[,options.time], input.data[,options.event]) ~ 1, data=input.data, type=options.type)
}

output.data <- fortify(km_fit)
output.data[sapply(output.data, is.infinite)] <- NA



if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)