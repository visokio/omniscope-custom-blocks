### Input fields

# defines the left join field
input.field.1 <- "Left field"

# defines the right join field
input.field.2 <- "Right field"

### Parameters

# defines the join type. Possible values are "left", "right", and "left+right". Left joins will find the best matches for all "left" terms, potentially not using all of the "right" terms. Right joins do the opposite. Left+Right joins append individual left and right joins.
join.type = "left+right"

### Script


library(data.table)
library(plyr)

possible.joins <- c("left", "right", "left+right")

# sanity checks
if (!exists("input.data")) stop("No 'left' input data")
if (!exists("input.data.2")) stop("No 'right' input data")
if (".index" %in% names(input.data) || ".index.x" %in% names(input.data) || ".index.y" %in% names(input.data)) stop("first input must not contain a field with name .index, .index.x or .index.y")
if (".index" %in% names(input.data.2) || ".index.x" %in% names(input.data.2) || ".index.y" %in% names(input.data.2)) stop("first input must not contain a field with name .index, .index.x or .index.y")
if (!(join.type %in% possible.joins)) stop("invalid join type")

# make join type into booleans
left.join <- F
if (join.type == "left" || join.type == "left+right")  left.join <- T
right.join <- F
if (join.type == "right" || join.type == "left+right")  right.join <- T

# extract text from input data
text.1 <- data.table(text = input.data[,input.field.1], check.names = T)
text.2 <- data.table(text = input.data.2[,input.field.2], check.names = T)

# convert to data.tables for later usage
setDT(input.data)
setDT(input.data.2)


split.into.terms <- function(x) {
  strsplit(x, "[^[:alpha:]]")
}

trim.terms <- function(x) {
  tolower(x[nchar(x) > 1])
}

create.terms <- function(data) {
  split.terms <- split.into.terms(data)
  trimmed.terms <- lapply(split.terms, trim.terms)
  
  terms <- unlist(trimmed.terms)
  counts <- laply(trimmed.terms, length)
  
  list(terms = terms, counts = counts)
}

# create new term indexes
create.indexes <- function(indexes.old, index.counts) {
  rep(indexes.old, times = index.counts)
}

# create data table of terms
create.term.table <- function(data) {
  data <- unlist(lapply(data, as.character))
  terms <- create.terms(data)
  index <- 1:length(data)
  
  index <- create.indexes(index, terms$counts)
  
  data.table(index = index, term = terms$terms)
}

# calculate inverse document frequencies
create.idf <- function(d) {
  result <- create.term.table(unlist(d$text))
  result[, in.doc.freq := 1.0/.N, by = term]
  result[, idf := log(.N * in.doc.freq)]
  result[, in.doc.freq := NULL]
  result
}

# calculate best term fits between x and y
best.fit <- function(x, y, turn) {
  merged.terms <- merge(x, y, by.x = "term", by.y = "term", allow.cartesian = T)
  scores <- merged.terms[, .(score = sum(idf.x)), by = .(index.x, index.y)]
  scores[, max.score := max(score), by = .(index.x)]
  
  scores[, best.index := score == max.score, by = .(index.x, index.y)]
  
  sw <- scores[best.index == TRUE]
  sw <- sw[, .(index.y = max(index.y)), by = index.x]
  if (turn) setnames(sw, c("index.x", "index.y"), c("index.y", "index.x"))
  sw
}

# convert texts into weighted terms
terms.1 <- create.idf(text.1)
terms.2 <- create.idf(text.2)

# calculate best fits between input 1 and input 2
if (left.join) bf.1 <- best.fit(terms.1, terms.2, F)
if (right.join) bf.2 <- best.fit(terms.2, terms.1, T)

# rename for safer merging
if (left.join) setnames(bf.1, c("index.x", "index.y"), c(".index.x", ".index.y"))
if (right.join) setnames(bf.2, c("index.x", "index.y"), c(".index.x", ".index.y"))

# create indexes for merging
input.data$.index <- 1:nrow(input.data)
input.data.2$.index <- 1:nrow(input.data.2)

# merge
if (left.join) data.x = merge(input.data, bf.1, by.x = ".index", by.y = ".index.x")
if (right.join) data.y = merge(input.data.2, bf.2, by.x = ".index", by.y = ".index.y")

# clean up
if (left.join) {
  data.x.merged <- merge(data.x, input.data.2, by.x = ".index.y", by.y = ".index")
  data.x.merged[, .index.y := NULL]
}
if (right.join) {
  data.y.merged <- merge(data.y, input.data, by.x = ".index.x", by.y = ".index")
  data.y.merged[, .index.x := NULL]
}

if (left.join && right.join) {
  output.data <- rbind(data.x.merged, data.y.merged)
} else {
  if (left.join) {
    output.data <- data.x.merged
  } else {
    output.data <- data.y.merged
  }
}

setorder(output.data, .index)
output.data[, .index := NULL]