# Writes the invented sample files for the R Data Reader block:
#   Rscript sample-data/make-sample-data.R   (from the block folder)
# store-survey.RData holds three objects, in this order: a note (text), the survey responses (data frame) and the
# stores (data frame with store codes as row names). stores.rds holds the stores on their own.

out <- if (dir.exists("sample-data")) "sample-data" else "."

survey_note <- "Customer survey, spring wave. Invented data for the R Data Reader demo."

set.seed(42)
store_codes <- c("BRI", "LDS", "NWC", "OXF")
responses <- data.frame(
  Response = sprintf("R-%03d", 1:24),
  Store = factor(rep(store_codes, each = 6), levels = store_codes),
  Visited = as.Date("2025-04-07") + rep(c(0, 1, 3, 4, 6, 9), 4),
  Score = c(9L, 7L, 8L, 10L, 6L, 9L, 5L, 7L, 6L, 8L, 4L, 7L, 8L, 9L, 9L, 10L, 7L, 8L, 6L, 6L, 7L, NA, 5L, 8L),
  Spend = round(c(42.5, 18.0, 63.2, 25.9, 12.4, 38.0, 22.1, 9.5, 31.0, 44.8, 15.2, 27.3,
                  51.6, 36.4, 19.9, 70.2, 28.8, 33.1, 14.6, 21.0, 26.7, 17.3, 8.9, 40.5), 2),
  Recommend = c(TRUE, TRUE, TRUE, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE,
                TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, TRUE, NA, FALSE, TRUE),
  stringsAsFactors = FALSE
)

stores <- data.frame(
  Town = c("Bristol", "Leeds", "Newcastle", "Oxford"),
  Opened = c(2016L, 2019L, 2021L, 2018L),
  Floorspace = c(1450, 2100, 1800, 1200),
  row.names = store_codes,
  stringsAsFactors = FALSE
)

save(survey_note, responses, stores, file = file.path(out, "store-survey.RData"), version = 2)
saveRDS(stores, file.path(out, "stores.rds"), version = 2)
