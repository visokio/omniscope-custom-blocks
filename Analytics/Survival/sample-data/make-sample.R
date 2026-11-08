# Writes subscriptions.csv: 180 invented subscriptions on two plans, followed for up to 24 months.
# Cancelled is 1 when the customer cancelled after Months, 0 when still subscribed at Months (censored).
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(2411)
n <- c(Monthly = 100, Annual = 80)
plan <- rep(names(n), n)
# months until cancelling: monthly plans leave faster; annual plans mostly leave at a renewal
lifetime <- ifelse(plan == "Monthly", ceiling(rweibull(sum(n), 1.1, 11)),
                   12 * ceiling(rweibull(sum(n), 1.4, 1.8)) - rbinom(sum(n), 1, 0.2))
# customers joined at different times, so each is followed for between 3 and 24 months
followed <- sample(3:24, sum(n), replace = TRUE)
months <- pmin(lifetime, followed)
cancelled <- as.integer(lifetime <= followed)
d <- data.frame(Customer = sprintf("S-%04d", seq_len(sum(n))), Plan = plan, Months = months, Cancelled = cancelled)
d <- d[sample(nrow(d)), ]
d$Customer <- sprintf("S-%04d", seq_len(nrow(d)))
d$Months[41] <- NA  # start date not recorded
write.csv(d, "sample-data/subscriptions.csv", row.names = FALSE, na = "")
