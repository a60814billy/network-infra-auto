import os
import re

from ..gitlab_api import GitLabCiApiClient

merge_request_iid = os.environ.get("CI_MERGE_REQUEST_IID", None)

gitlab_client = GitLabCiApiClient()

device_parse_re = re.compile(r"^cfg/(.*)\.cfg$")


def get_mr_change_files():
    changeset = gitlab_client.get_mr_change_files()["changes"]
    device_list = []

    for change in changeset:
        # if new_path is in cfg/
        if change["new_path"].startswith("cfg/"):
            # use filename to get the device host
            device = device_parse_re.search(change["new_path"]).group(1)
            device_list.append(device)

    return device_list


def get_merged_mr_changes():
    # use git command to get diff file names
    diff_cmd = "git diff --name-only HEAD^1 HEAD cfg/"
    diff_files = os.popen(diff_cmd).read().splitlines()
    device_list = []
    for file in diff_files:
        device = device_parse_re.search(file).group(1)
        device_list.append(device)

    return device_list


def detect_cfg_changes() -> None:
    if merge_request_iid:
        device_list = get_mr_change_files()
    else:
        device_list = get_merged_mr_changes()

    for device in device_list:
        print(device)
