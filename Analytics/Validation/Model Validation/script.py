from omniscope.api import OmniscopeApi
from sklearn.metrics import confusion_matrix
from sklearn.metrics import precision_recall_fscore_support
import pandas as pd
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
ground_truth_field = omniscope_api.get_option("ground_truth")
prediction_field = omniscope_api.get_option("prediction")

ground_truth = input_data[ground_truth_field]
prediction = input_data[prediction_field]

labels = prediction.unique()

mat = confusion_matrix(ground_truth, prediction, labels=labels)

output_data = pd.DataFrame(mat)
output_data.insert(0, "category",labels)
header = ["category"]
header.extend(labels.tolist())

output_data.columns = header

macro = ["macro"]
macro.extend(list(precision_recall_fscore_support(ground_truth, prediction, average = "macro"))[0:3])
micro = ["micro"]
micro.extend(list(precision_recall_fscore_support(ground_truth, prediction, average = "micro"))[0:3])
weighted = ["weighted"]
weighted.extend(list(precision_recall_fscore_support(ground_truth, prediction, average = "weighted"))[0:3])

output_data_2 = pd.DataFrame(columns=["averaging", "precision", "recall", "fscore"])

print("MAC" + str(macro))
print("MIC" + str(micro))
print("WGH" + str(weighted))

output_data_2.loc[len(output_data_2)] = macro
output_data_2.loc[len(output_data_2)] = micro
output_data_2.loc[len(output_data_2)] = weighted








#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
    
if output_data_2 is not None:
	omniscope_api.write_output_records(output_data_2, output_number=1)
omniscope_api.close()