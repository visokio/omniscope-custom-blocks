from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

class JiraAPI:
    def __init__(self, base_url, username, api_token):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, api_token)

    def get_projects(self):
        response = requests.get(f"{self.base_url}/rest/api/2/project", auth=self.auth)
        response.raise_for_status()
        projects = response.json()
        return pd.DataFrame(projects)

    def get_project_ids(self):
        projects_df = self.get_projects()
        return projects_df['id']

    def get_issues(self, project_key):
        response = requests.get(f"{self.base_url}/rest/api/2/search?jql=project={project_key}", auth=self.auth)
        response.raise_for_status()
        issues = response.json()['issues']
        # normalize the issues json
        return pd.json_normalize(issues)

    def get_user(self, username):
        response = requests.get(f"{self.base_url}/rest/api/2/user?username={username}", auth=self.auth)
        response.raise_for_status()
        return pd.DataFrame([response.json()])

    def get_issue(self, issue_key):
        response = requests.get(f"{self.base_url}/rest/api/2/issue/{issue_key}", auth=self.auth)
        response.raise_for_status()
        return pd.DataFrame([response.json()])


jiraInstance = omniscope_api.get_option("jiraInstance")
username = omniscope_api.get_option("username")
apiToken = omniscope_api.get_option("apiKey")

projectID = omniscope_api.get_option("projectID")

jira = JiraAPI(f'https://{jiraInstance}.atlassian.net', username, apiToken)

# Get all projects as DataFrame
projects_df = jira.get_projects()

if projects_df is not None:
    omniscope_api.write_output_records(projects_df, output_number=0)

if (projectID is not None):
    # Get all issues in a specific project as DataFrame
    issues_df = jira.get_issues(projectID)
    if (issues_df is not None):
         print(issues_df)
         omniscope_api.write_output_records(issues_df, output_number=1)



# Get a specific issue as DataFrame
#issue_df = jira.get_issue('PROJKEY-1')
#print(issue_df)



omniscope_api.close()