from omniscope.api import OmniscopeApi
import markdown, pandas as pd
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

htmls = []
for index, row in input_data.iterrows():
   md_text = row[omniscope_api.get_option('MarkdownText')]
   html = markdown.markdown(md_text)
   htmls.append(html)
   
output_data = pd.DataFrame(htmls,columns=['HTML'])

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()