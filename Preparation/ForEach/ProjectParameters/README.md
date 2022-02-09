### For each row of the input data, sets the values of some defined project parameters.

The input data should have a field containing the project IOX URLs ( *e.g. http://127.0.0.1:24679/Folder/MyProject.iox/* ) , 
together with one or more fields used to set the project parameters (e.g. a field called *MyParam* containing value *MyValue* will result into setting the value *MyValue* in the project parameter named *MyParam*)

The block uses workflow public APIS described [here](https://help.visokio.com/support/solutions/articles/42000073133-workflow-execution-rest-apis).
