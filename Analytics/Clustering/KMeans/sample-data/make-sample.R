# Writes store-metrics.csv: invented weekly figures for 80 shops in four formats.
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(20261106)
formats <- data.frame(
  Format = c("Convenience", "Supermarket", "Superstore", "Forecourt"),
  n = c(24, 22, 14, 20),
  sales = c(38000, 115000, 260000, 52000), sales_sd = c(5000, 12000, 25000, 6000),
  footfall = c(9500, 14000, 21000, 4200), footfall_sd = c(1200, 1600, 2200, 700)
)
rows <- do.call(rbind, lapply(seq_len(nrow(formats)), function(i) {
  f <- formats[i, ]
  data.frame(Format = f$Format,
             `Weekly Sales` = round(rnorm(f$n, f$sales, f$sales_sd), 2),
             Footfall = as.integer(round(rnorm(f$n, f$footfall, f$footfall_sd))),
             check.names = FALSE)
}))
rows <- rows[sample(nrow(rows)), ]
regions <- c("North", "Midlands", "South", "Wales", "Scotland")
out <- data.frame(Store = sprintf("ST-%03d", seq_len(nrow(rows))),
                  Region = sample(regions, nrow(rows), replace = TRUE),
                  rows, check.names = FALSE)
out$Footfall[17] <- NA  # one shop's door counter was broken that week
# Format is kept out of the sample file: it is what the clustering should find. Tests read it from here.
write.csv(out[, c("Store", "Region", "Weekly Sales", "Footfall")], "sample-data/store-metrics.csv",
          row.names = FALSE, na = "")
write.csv(out[, c("Store", "Format")], "tests/store-formats.csv", row.names = FALSE)
