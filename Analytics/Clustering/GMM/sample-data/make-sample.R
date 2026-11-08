# Writes pump-readings.csv (150 invented readings from one pump in three operating modes) and
# new-readings.csv (12 later readings to assign to those modes).
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(611)
modes <- list(
  Idle   = list(n = 50, mu = c(41, 1.2), sd = c(1.5, 0.15), r = 0.2),
  Normal = list(n = 60, mu = c(58, 3.0), sd = c(4.0, 0.45), r = 0.85),
  Heavy  = list(n = 40, mu = c(74, 4.6), sd = c(3.5, 0.9), r = -0.3)
)
draw <- function(m, n) {
  z1 <- rnorm(n); z2 <- m$r * z1 + sqrt(1 - m$r^2) * rnorm(n)
  data.frame(Temperature = round(m$mu[1] + m$sd[1] * z1, 1), Vibration = round(m$mu[2] + m$sd[2] * z2, 2))
}
make <- function(counts, prefix, start) {
  rows <- do.call(rbind, lapply(names(counts), function(k) cbind(Mode = k, draw(modes[[k]], counts[[k]]))))
  rows <- rows[sample(nrow(rows)), ]
  t0 <- as.POSIXct(start, tz = "UTC")
  data.frame(Reading = sprintf("%s-%04d", prefix, seq_len(nrow(rows))),
             Time = format(t0 + 3600 * seq_len(nrow(rows)) - 3600, "%Y-%m-%d %H:%M"),
             rows[, c("Temperature", "Vibration")], Mode = rows$Mode)
}
train <- make(list(Idle = 50, Normal = 60, Heavy = 40), "R", "2026-09-01 00:00")
train$Vibration[23] <- NA  # a dropped sensor reading
new <- make(list(Idle = 4, Normal = 5, Heavy = 3), "N", "2026-09-08 00:00")
# Mode is kept out of the sample files: it is what the clustering should find. Tests read it from here.
write.csv(train[, 1:4], "sample-data/pump-readings.csv", row.names = FALSE, na = "")
write.csv(new[, 1:4], "sample-data/new-readings.csv", row.names = FALSE, na = "")
write.csv(rbind(train, new)[, c("Reading", "Mode")], "tests/pump-modes.csv", row.names = FALSE)
