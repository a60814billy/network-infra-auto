import os

from gitlab_api import GitLabCiApiClient

CHANGED_DEVICE_LIST_FILE = ".change_device_list"

def main():
    gitlab_client = GitLabCiApiClient()
    default_branch = os.environ.get("CI_DEFAULT_BRANCH", None)

    # Read the change device list file if it exists
    device_list_content = ""
    if os.path.exists(CHANGED_DEVICE_LIST_FILE):
        with open(CHANGED_DEVICE_LIST_FILE, "r") as f:
            device_list_content = f.read()
        print(f"Found .change_device_list with content: {device_list_content}")
    else:
        print("Warning: .change_device_list file not found")

    print(f"Triggering post-deploy pipeline on branch {default_branch}...")
    pipeline = gitlab_client.trigger_pipeline(default_branch, [{
        "key": "CHANGE_DEVICE_LIST",
        "value": device_list_content
    }])
    pipeline_id = pipeline.get('id')
    print(f"Successfully triggered post-deploy pipeline with ID: {pipeline_id}")

if __name__ == "__main__":
    main()