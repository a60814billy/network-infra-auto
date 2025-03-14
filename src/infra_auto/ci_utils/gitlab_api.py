import os
import urllib.parse

import requests


class GitLabClient:
    def __init__(self, endpoint: str, token: str):
        self.api_endpoint = endpoint
        self.api_token = token
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": self.api_token})

    def get_mr_change_files(self, project_id: str, merge_request_iid: str):
        resp = self.session.get(
            f"{self.api_endpoint}/projects/{project_id}/merge_requests/{merge_request_iid}/changes"
        )

        if resp.status_code > 299 or resp.status_code < 200:
            raise Exception(f"Failed to get changes: {resp.text}")

        return resp.json()

    def post_mr_note(self, project_id: str, merge_request_iid: str, body: str):
        resp = self.session.post(
            f"{self.api_endpoint}/projects/{project_id}/merge_requests/{merge_request_iid}/notes?body={urllib.parse.quote(body)}"
        )

        if resp.status_code > 299 or resp.status_code < 200:
            raise Exception(f"Failed to post note: {resp.text}")

        return resp.json()

    def trigger_pipeline(self, project_id: str, branch: str, variables: list):

        default_variables = [{"key": "CI_PIPELINE_SOURCE", "value": "api"}]

        # remove duplicates in variables
        for default_var in default_variables:
            for var in variables:
                if var["key"] == default_var["key"]:
                    default_variables.remove(default_var)

        vars = default_variables.extend(variables)

        resp = self.session.post(
            f"{self.api_endpoint}/projects/{project_id}/pipeline",
            json={"ref": branch, "variables": vars},
        )

        if resp.status_code != 200:
            raise Exception(f"Failed to trigger pipeline: {resp.text}")

        return resp.json()


class GitLabCiApiClient(GitLabClient):
    def __init__(self):
        endpoint = os.environ.get("CI_API_V4_URL")
        token = os.environ.get("GITLAB_API_TOKEN")

        super().__init__(endpoint, token)

        self.project_id = os.environ.get("CI_PROJECT_ID")
        self.merge_request_iid = os.environ.get("CI_MERGE_REQUEST_IID", None)

    def get_mr_change_files(self):
        return super().get_mr_change_files(self.project_id, self.merge_request_iid)

    def post_mr_note(self, body: str):
        return super().post_mr_note(self.project_id, self.merge_request_iid, body)

    def trigger_pipeline(self, branch: str, variables: list):
        return super().trigger_pipeline(self.project_id, branch, variables)
