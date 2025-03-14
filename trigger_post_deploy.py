import os
import requests
import time

# GitLab API configuration
gitlab_api_url = "http://10.192.4.172/api/v4"
project_id = os.environ["CI_PROJECT_ID"]
api_token = os.environ["GITLAB_API_TOKEN"]
default_branch = os.environ["CI_DEFAULT_BRANCH"]

# Wait for a short time to ensure the current pipeline completes
print("Waiting for current pipeline to complete...")
time.sleep(3)

# Trigger a new pipeline via GitLab API
print(f"Triggering post-deploy pipeline on branch {default_branch}...")
response = requests.post(
    f'{gitlab_api_url}/projects/{project_id}/pipeline',
    headers={'PRIVATE-TOKEN': api_token},
    json={
        "ref": default_branch,
        "variables": [
            {
                "key": "CI_PIPELINE_SOURCE",
                "value": "api"
            }
        ]
    }
)

# Check response
if response.status_code >= 200 and response.status_code < 300:
    pipeline_data = response.json()
    pipeline_id = pipeline_data.get('id')
    print(f"Successfully triggered post-deploy pipeline with ID: {pipeline_id}")
    print(f"Pipeline URL: {gitlab_api_url}/projects/{project_id}/pipelines/{pipeline_id}")
else:
    print(f"Failed to trigger post-deploy pipeline. Status code: {response.status_code}")
    print(f"Response: {response.text}")
