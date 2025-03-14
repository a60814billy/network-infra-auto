import os
from infra_auto.ci_utils.gitlab_api import GitLabCiApiClient

def report_changes_to_mr_comment(report_file_name: str):
    if not os.path.exists(report_file_name):
        raise FileNotFoundError(f"File {report_file_name} not found")

    gitlab_client = GitLabCiApiClient()

    with open(report_file_name) as f:
        output = f.read()
    
    output = '### Nornir Dry Run Output\n```\n' + output + '\n```\n'

    gitlab_client.post_mr_note(output)
