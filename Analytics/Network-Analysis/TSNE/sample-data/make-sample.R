# Writes email-network.csv: invented counts of e-mails between 60 staff in three teams over a quarter.
# Each record is one sender, one recipient and the number of e-mails; most go to people in the same team.
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(314)
teams <- c(Finance = 18, Logistics = 22, Product = 20)
staff <- data.frame(Name = sprintf("%s-%02d", rep(substr(names(teams), 1, 3), teams), sequence(teams)),
                    Team = rep(names(teams), teams), stringsAsFactors = FALSE)
rows <- list()
for (i in seq_len(nrow(staff))) {
  same <- setdiff(which(staff$Team == staff$Team[i]), i)
  other <- which(staff$Team != staff$Team[i])
  to <- c(sample(same, sample(4:7, 1)), sample(other, sample(0:1, 1)))
  rows[[i]] <- data.frame(From = staff$Name[i], To = staff$Name[to],
                          Emails = as.integer(rpois(length(to), 12) + 1), stringsAsFactors = FALSE)
}
d <- do.call(rbind, rows)
d$Emails[5] <- NA  # count not recorded
write.csv(d, "sample-data/email-network.csv", row.names = FALSE, na = "")
# Each person's team, used by the tests to check that teams end up together on the map
write.csv(staff, "tests/teams.csv", row.names = FALSE)
