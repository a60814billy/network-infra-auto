from infra_auto.ci_utils.gitlab_api import GitLabCiApiClient

def main():
    gitlab_client = GitLabCiApiClient()

    with open('.dry_run_output') as f:
        output = f.read()
    
    output = '### Nornir Dry Run Output\n```\n' + output + '\n```\n'

    gitlab_client.post_mr_note(output)


if __name__ == '__main__':
    main()
