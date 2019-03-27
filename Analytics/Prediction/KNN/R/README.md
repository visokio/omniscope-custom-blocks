# K-Nearest-Neighbours

Performs k-nearest-neighbour prediction on the data. The prediction for a new point depends on the k-nearest-neighbours around the point. The majority class is used as the prediction.

## Language
R

## Parameters
### fields.to.use
Adjust to fields you want to use in the prediction.
### field.to.predict
The field which is unknwon in the new data you want to predict.
### use.all.numeric.fields
If set to true, fields.to.use will be ignored and instead all numeric data fields used.
### k.nearest.neighbours
The k in k-nearest-neighbours. I.e. the number of points around a point of unknown class to take into account.
## Dependencies
class

## Source
[knn.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/KNN/R/knn.R)
