from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()



from github import Github
from github import InputGitTreeElement
import pandas as pd
import io
import base64
import zlib

repository_path = omniscope_api.get_option("repositoryPath")
file_path = omniscope_api.get_option("filePath")
github_token = omniscope_api.get_option("githubToken")
mode = omniscope_api.get_option("mode")
compressed = omniscope_api.get_option("compressed")

if github_token is not None:
	g = Github(github_token)
else:
	g = Github()
    
try:
	repo = g.get_repo(repository_path)
except Exception as e:
	omniscope_api.cancel("Repository path is invalid: " + str(e))

separator = omniscope_api.get_option("separator")
if separator is None or len(separator) == 0: separator = ","

def get_master_ref():
	return(repo.get_git_refs()[0])

def get_master_sha():
	ref = get_master_ref()
	return(ref.object.sha)

def get_base_tree(recursive):
	tree = repo.get_git_tree(get_master_sha(), recursive=recursive)
	return(tree)

def get_sha(file_path):

	sha = None
	try:
		
		tree = get_base_tree(True)
		for e in tree.tree:
			if e.path == file_path:
				sha = e.sha
	except Exception as e:
		omniscope_api.cancel("File path is invalid: " + str(e))

	return(sha)






if mode == "READ":

	sha = get_sha(file_path)
    
	if sha is None:
		omniscope_api.cancel("file not found")

	try:
		blob = repo.get_git_blob(sha)
	except Exception as e:
		omniscope_api.cancel("Blob is invalid: " + str(e))
        
	content = base64.b64decode(blob.content)
	if compressed:
		try:
			content = zlib.decompress(content)
		except Exception as e:
			omniscope_api.cancel("Failed decompress data. Is it really compressed? " + str(e))

	try:
		content = content.decode("utf-8")
	except Exception as e:
		omniscope_api.cancel("Failed to read data. Is it compressed? " + str(e))

	try:
		df = pd.read_csv(io.StringIO(content), sep=separator)
	except:
		d = {"content": content}
		try:
			df = pd.DataFrame(data=d)
		except Exception as e:
			omniscope_api.cancel("Cannot create data frame from data: " + str(e))

	output_data = df

	if output_data is not None:
		omniscope_api.write_output_records(output_data, output_number=0)

if mode == "WRITE":

	try:
		input_data = omniscope_api.read_input_records(input_number=0)
		csv = input_data.to_csv(sep = separator, index = False).encode("UTF-8")
        
		if compressed: csv = zlib.compress(csv)
        
		data = base64.b64encode(csv)
		blob = repo.create_git_blob(data.decode("utf-8"), "base64")
		element = InputGitTreeElement(path=file_path, mode='100644', type='blob', sha=blob.sha)
		master_sha = get_master_sha()
		base_tree = get_base_tree(False)
		new_tree = repo.create_git_tree([element], base_tree)
		parent = repo.get_git_commit(master_sha)
		commit = repo.create_git_commit("adding file", new_tree, [parent])
		get_master_ref().edit(commit.sha)
    
	except Exception as e:
	      omniscope_api.cancel("Cannot upload blob: " + str(e))
        
        
omniscope_api.close()