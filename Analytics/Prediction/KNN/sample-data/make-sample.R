# Writes known-customers.csv (120 invented customers whose segment is known, plus 6 not yet assigned) and
# new-customers.csv (15 new customers to classify).
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(4242)
segments <- list(
  "Bargain hunter"   = list(spend = c(950, 220), orders = c(22, 4), discount = c(24, 4)),
  "Loyal regular"    = list(spend = c(1150, 260), orders = c(26, 5), discount = c(6, 2.5)),
  "Big-ticket buyer" = list(spend = c(2600, 500), orders = c(4, 1.5), discount = c(9, 3.5))
)
draw <- function(seg, n) {
  s <- segments[[seg]]
  data.frame(`Annual Spend` = round(pmax(50, rnorm(n, s$spend[1], s$spend[2])), 2),
             `Orders Per Year` = as.integer(pmax(1, round(rnorm(n, s$orders[1], s$orders[2])))),
             `Average Discount` = round(pmin(40, pmax(0, rnorm(n, s$discount[1], s$discount[2]))), 1),
             Segment = seg, check.names = FALSE)
}
make <- function(counts, prefix) {
  rows <- do.call(rbind, lapply(names(counts), function(g) draw(g, counts[[g]])))
  rows <- rows[sample(nrow(rows)), ]
  cbind(Customer = sprintf("%s-%04d", prefix, seq_len(nrow(rows))), rows)
}
known <- make(list("Bargain hunter" = 42, "Loyal regular" = 46, "Big-ticket buyer" = 38), "C")
truth.known <- known$Segment
unassigned <- c(9, 31, 58, 77, 102, 118)
known$Segment[unassigned] <- NA  # not yet assigned by the account team
new <- make(list("Bargain hunter" = 5, "Loyal regular" = 6, "Big-ticket buyer" = 4), "N")
write.csv(known, "sample-data/known-customers.csv", row.names = FALSE, na = "")
write.csv(new[, 1:4], "sample-data/new-customers.csv", row.names = FALSE, na = "")
# The true segment of every customer, used by the tests
write.csv(data.frame(Customer = c(known$Customer, new$Customer), Segment = c(truth.known, new$Segment)),
          "tests/true-segments.csv", row.names = FALSE)
