import json
from lib.git import add_note_to_mr
from lib.aikido import generate_issue_table
import os
import argparse

project_url = os.getenv("CI_PROJECT_URL")
source_branch_name = os.getenv("CI_COMMIT_REF_NAME")
pipeline_id = os.getenv("CI_PIPELINE_ID")
pipeline_url = os.getenv("CI_PIPELINE_URL")
commit_sha = os.getenv("CI_COMMIT_SHA")
project_name = os.getenv("CI_PROJECT_NAME")

aikido_client_id = os.getenv("AIKIDO_CLIENT_ID")
aikido_client_secret = os.getenv("AIKIDO_CLIENT_SECRET")

disable_quotes = os.getenv("DISABLE_QUOTES", False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse trufflehog output")
    parser.add_argument(
        "--gitlab-url",
        help="URI to gitlab instance",
        required=False,
        type=str,
        default=os.getenv("CI_SERVER_URL"),
    )
    parser.add_argument(
        "--gitlab-token",
        help="Gitlab access token",
        required=False,
        type=str,
        default=os.getenv("GL_TOKEN"),
    )
    parser.add_argument(
        "--repo-id",
        help="Gitlab repo id",
        required=False,
        type=int,
        default=os.getenv("CI_PROJECT_ID"),
    )
    parser.add_argument(
        "--mr-iid",
        help="Merge request iid",
        required=False,
        type=int,
        default=os.getenv("CI_MERGE_REQUEST_IID"),
    )

    return parser.parse_args()


def main():

    args: argparse.Namespace = parse_args()

    if args.mr_iid is None:
        print("Not running in merge request")
        exit(0)

    ex = 0
    for arg, value in args._get_kwargs():
        if value is None:
            print(f"Argument {arg} is not set")
            ex = 1
    if ex:
        exit(1)

    print("Generating aikido scan results table...")

    # get repo name from environment
    repo_name = os.getenv("CI_PROJECT_NAME")
    if repo_name is None:
        raise Exception("CI_PROJECT_NAME not set in environment")
    try:
        aikido_table = generate_issue_table(
            aikido_client_id, aikido_client_secret, repo_name
        )
    except Exception as e:
        aikido_table = "\nFailed to generate Aikido table\n"
        print(f"Failed to generate Aikido table: {e}")

    base_message = f"# Security tooling scan results\n\n|   |   |\n|---|---|\n|Pipeline ID|[{pipeline_id}]({pipeline_url})|\n|Commit sha1|{commit_sha}|\n\n"
    message = f"{base_message}\n\n{aikido_table}"

    add_note_to_mr(
        args.gitlab_url,
        args.gitlab_token,
        args.repo_id,
        args.mr_iid,
        message,
    )


main()
