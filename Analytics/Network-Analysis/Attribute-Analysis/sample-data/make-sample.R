# Writes project-assignments.csv: invented assignments of staff (in 5 departments) to 16 projects. Teams are drawn
# from a pool of 40 people; with this seed 36 of them are drawn, so the file has 36 people.
# Each record is one person working on one project; Department is the person's department.
#   Rscript sample-data/make-sample.R   (from the block folder)
set.seed(77)
depts <- c("Sales", "Marketing", "Engineering", "Operations", "Finance")
staff <- data.frame(Person = sprintf("P%02d", 1:40), Department = rep(depts, times = c(10, 6, 12, 8, 4)))
# Each project has a lead department and draws most of its team from the departments it works with
projects <- data.frame(
  Project = sprintf("PRJ-%02d", 1:16),
  Mix = c(rep("Sales+Marketing", 5), rep("Engineering+Operations", 5), rep("Sales+Finance", 2),
          rep("Operations+Finance", 2), "Engineering+Marketing", "Engineering"))
rows <- list()
for (i in seq_len(nrow(projects))) {
  team.depts <- strsplit(projects$Mix[i], "+", fixed = TRUE)[[1]]
  size <- sample(4:7, 1)
  # at least one person from each department in the mix, the rest from either
  first <- do.call(rbind, lapply(team.depts, function(dd) { p <- staff[staff$Department == dd, ]; p[sample(nrow(p), 1), ] }))
  pool <- staff[staff$Department %in% team.depts & !(staff$Person %in% first$Person), ]
  team <- rbind(first, pool[sample(nrow(pool), size - nrow(first)), ])
  rows[[i]] <- data.frame(Person = team$Person, Project = projects$Project[i], Department = team$Department)
}
d <- do.call(rbind, rows)
d <- d[order(d$Project, d$Person), ]
d$Department[7] <- NA  # department not recorded for one assignment
write.csv(d, "sample-data/project-assignments.csv", row.names = FALSE, na = "")
