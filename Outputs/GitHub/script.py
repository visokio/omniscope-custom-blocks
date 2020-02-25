from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()



from github import Github
import pandas as pd
import io

repository_path = omniscope_api.get_option("repositoryPath")
file_path = omniscope_api.get_option("filePath")
github_token = omniscope_api.get_option("githubToken")
mode = omniscope_api.get_option("mode")


if github_token is not None:
	g = Github(github_token)
else:
	g = Github()
    
try:
	repo = g.get_repo(repository_path)
except Exception as e:
	omniscope_api.cancel("repository path is invalid: " + str(e))

separator = omniscope_api.get_option("separator")
if separator is None or len(separator) == 0: separator = ","

if mode == "READ":

	try:
		file = repo.get_contents(file_path)
	except Exception as e:
		omniscope_api.cancel("file path is invalid: " + str(e))

	content = file.decoded_content.decode("utf-8")


	try:
		df = pd.read_csv(io.StringIO(content), sep=separator)
	except:
		d = {"content": content}
		try:
			df = pd.DataFrame(data=d)
		except Exception as e:
			omniscope_api.cancel("cannot create data frame from data: " + str(e))

	output_data = df

	if output_data is not None:
		omniscope_api.write_output_records(output_data, output_number=0)

if mode == "WRITE":
	input_data = omniscope_api.read_input_records(input_number=0)
	content = input_data.to_csv(sep = separator)
	try:
		file = repo.get_contents(file_path)
		repo.update_file(file_path, message="updating file", sha=file.sha, content=content)
	except Exception as e:
		repo.create_file(file_path, message="adding file", content=content)
        
        
        
omniscope_api.close()