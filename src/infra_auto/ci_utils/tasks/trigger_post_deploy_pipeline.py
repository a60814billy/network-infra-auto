import os

from infra_auto.ci_utils.gitlab_api import GitLabCiApiClient


def trigger_post_deploy_pipeline(device_list_file: str):
    gitlab_client = GitLabCiApiClient()
    default_branch = os.environ.get("CI_DEFAULT_BRANCH", None)

    if not os.path.exists(device_list_file):
        raise FileNotFoundError(f"File {device_list_file} not found")

    # Read the change device list file if it exists
    with open(device_list_file, "r") as f:
        device_list_content = f.read()
    print(f"Found .change_device_list with content: {device_list_content}")

    print(f"Triggering post-deploy pipeline on branch {default_branch}...")
    pipeline = gitlab_client.trigger_pipeline(
        default_branch, [{"key": "CHANGE_DEVICE_LIST", "value": device_list_content}]
    )
    pipeline_id = pipeline.get("id")
    print(f"Successfully triggered post-deploy pipeline with ID: {pipeline_id}")
