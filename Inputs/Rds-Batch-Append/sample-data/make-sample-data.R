# Writes the invented sample files for the Rds Batch Append block:
#   Rscript sample-data/make-sample-data.R   (from the block folder)
# Three monthly extracts of branch sales, as a reporting job in R might save them. They don't quite agree:
# March adds a branch and a Returns field, and its Orders are stored as decimals rather than whole numbers.

out <- file.path(if (dir.exists("sample-data")) "sample-data" else ".", "monthly-sales")
dir.create(out, showWarnings = FALSE)

branches <- c("Bath", "Chester", "Durham", "Exeter", "Norwich")

january <- data.frame(
  Branch = factor(branches),
  Month = as.Date("2025-01-01"),
  Orders = c(412L, 298L, 175L, 233L, 341L),
  Revenue = c(18540.20, 12011.75, 7340.00, 9925.40, 14388.10)
)
february <- data.frame(
  Branch = factor(branches),
  Month = as.Date("2025-02-01"),
  Orders = c(388L, 305L, 169L, 241L, 322L),
  Revenue = c(17320.55, 12460.10, 7012.35, 10230.00, 13675.80)
)
march <- data.frame(
  Branch = factor(c(branches, "Lincoln")),
  Month = as.Date("2025-03-01"),
  Orders = c(430, 321, 181, 256, 350, 64),
  Revenue = c(19275.00, 13104.60, 7598.25, 10870.90, 14902.30, 2650.00),
  Returns = c(12L, 7L, 3L, 9L, 11L, 0L)
)

saveRDS(january, file.path(out, "sales-2025-01.rds"), version = 2)
saveRDS(february, file.path(out, "sales-2025-02.rds"), version = 2)
saveRDS(march, file.path(out, "sales-2025-03.rds"), version = 2)
