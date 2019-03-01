### Parameters

# replace the left fields with fields from input.data, and the right fields with fields from input.data.2
# allowed equality/inequality comparators are ==, <=, >=, <, >
join.on = quote(list(Left.Field.1 == Right.Field.2, Left.Field.2 >= Right.Field.3, Left.Field.3 < Right.Field.4))

### Script


library(data.table)

# sanity checks
if (!exists("input.data")) stop("No 'left' input data")
if (!exists("input.data.2")) stop("No 'right' input data")

left <- input.data
setDT(left)

right <- input.data.2
setDT(right)

output.data <- input.data[input.data.2, on = eval(join.on), allow.cartesian = T, nomatch=0]
