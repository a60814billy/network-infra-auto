import os
import urllib.parse

import requests

gitlab_api_url = "http://10.192.4.172/api/v4"

project_id = os.environ["CI_PROJECT_ID"]
merge_request_iid = os.environ["CI_MERGE_REQUEST_IID"]
api_token = os.environ["GITLAB_API_TOKEN"]

with open('.dry_run_output') as f:
    output = f.read()

output = '### Nornir Dry Run Output\n```\n' + output + '\n```\n'

requests.post(
    f'{gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/notes?body={urllib.parse.quote(output)}',
    headers={'PRIVATE-TOKEN': api_token}
)
