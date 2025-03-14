import os
import re

import requests

gitlab_api_url = "http://10.192.4.172/api/v4"

project_id = os.environ["CI_PROJECT_ID"]
merge_request_iid = os.environ.get("CI_MERGE_REQUEST_IID", None)
api_token = os.environ["GITLAB_API_TOKEN"]

device_parse_re = re.compile(r'^cfg/(.*)\.cfg$')


def get_mr_change_files():
    resp = requests.get(
        f'{gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/changes',
        headers={'PRIVATE-TOKEN': api_token}
    )

    if resp.status_code != 200:
        raise Exception(f'Failed to get changes: {resp.text}')

    changes = resp.json()
    changeset = changes['changes']

    device_list = []

    for change in changeset:
        # if new_path is in cfg/
        if change['new_path'].startswith('cfg/'):
            # use filename to get the device host
            device = device_parse_re.search(change['new_path']).group(1)
            device_list.append(device)

    return device_list


def get_merged_mr_changes():
    # use git command to get diff file names
    diff_cmd = 'git diff --name-only HEAD^1 HEAD cfg/'
    diff_files = os.popen(diff_cmd).read().splitlines()
    device_list = []
    for file in diff_files:
        device = device_parse_re.search(file).group(1)
        device_list.append(device)

    return device_list


def main():
    if merge_request_iid:
        print('Getting MR changes')
        device_list = get_mr_change_files()
    else:
        print('Getting merged MR changes')
        device_list = get_merged_mr_changes()

    with open('.change_device_list', 'w') as f:
        for device in device_list:
            f.write(f'{device}\n')


if __name__ == '__main__':
    main()
