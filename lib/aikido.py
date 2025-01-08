import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any
import concurrent.futures
import os

project_url = os.getenv("CI_PROJECT_URL")
source_branch_name = os.getenv("CI_COMMIT_REF_NAME")


def get_oauth_token(client_id: str, client_secret: str) -> str:
    """
    This function implements the OAuth 2.0 client credentials flow by making a POST request
    to Aikido's token endpoint. It authenticates using the provided client credentials
    to obtain an access token required for API authorization.

    Args:

        client_id (str): The client ID obtained from Aikido platform for API authentication
        client_secret (str): The client secret obtained from Aikido platform for API authentication

    Returns:

        str: The OAuth access token string that can be used for subsequent API calls

    Exceptions:

        If the API request fails or returns a non-200 status code
        requests.exceptions.RequestException: If there are network/connection issues
        JSONDecodeError: If the API response cannot be parsed as JSON

    Example:
        ```
        >>> token = get_oauth_token("client_123", "secret_456")
        >>> print(token)
        'eyJ0eXAiOiJKV1QiLCJhbGc...'
        ```

    Notes:
        - The token endpoint used is https://app.aikido.dev/api/oauth/token
        - The function uses HTTP Basic Auth with the client credentials
        - The grant_type is set to "client_credentials" as per OAuth 2.0 specification
    """

    # https://apidocs.dev/reference/getaccesstoken
    token_url = "https://app.aikido.dev/api/oauth/token"
    data = {"grant_type": "client_credentials"}

    response = requests.post(
        token_url, data=data, auth=HTTPBasicAuth(client_id, client_secret)
    )

    if response.status_code == 200:
        # Parse the JSON response to get the access token
        token_info = response.json()
        access_token = token_info.get("access_token")

        return access_token
    else:
        raise Exception("Unable to retrieve access token")


def get_code_repositories(access_token: str) -> List[Dict[str, Any]]:
    """
    Retrieve the list of code repositories from Aikido's API using pagination.

        This function makes authenticated requests to the Aikido API to fetch all available code repositories.
        It handles pagination automatically by making multiple requests until all repositories are retrieved.

            access_token (str): The OAuth2 access token used for API authentication.

            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains repository details.
            Each dictionary includes repository properties as defined in the Aikido API specification.

            Exception: If any API request fails, including:
                - Authentication errors (401)
                - Authorization errors (403)
                - Server errors (500)
                - Any other non-200 status code

        Example:
            ```
            >>> access_token = "your_oauth_token"
            >>> repositories = get_code_repositories(access_token)
            >>> print(f"Found {len(repositories)} repositories")
            ```

        Notes:
            - Makes paginated requests with 10 results per page
            - Continues fetching until all repositories are retrieved
            - API endpoint: https://app.aikido.dev/api/public/v1/repositories/code
    """
    # https://apidocs.dev/reference/listcoderepos
    url = "https://app.aikido.dev/api/public/v1/repositories/code"
    results_per_page = 10

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    page = 0
    params = {"per_page": f"{results_per_page}", "page": f"{page}"}

    repos = []
    while True:
        params.update({"page": f"{page}"})

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:

            repos = repos + response.json()
        else:
            raise Exception(
                f"Failed to retrieve code repositories: {response.status_code} - {response.text}"
            )
        if len(response.json()) < results_per_page:
            break
        page += 1
    return repos


def get_repo_id(repos: List[Dict[str, Any]], repo_name: str) -> str:
    """
    Get the repository ID for a given repository name.

    Args:
        repos (List[Dict[str, Any]]): List of repositories.
        repo_name (str): Name of the repository to search for.

    Returns:
        str: The repository ID if found, otherwise an empty string.
    """
    for repo in repos:
        if repo_name in repo["name"]:
            return repo["id"]

    raise Exception("Unable to find repo ID!")


def get_open_issue_groups(access_token: str, repo_id: str) -> List[Dict[str, Any]]:
    """
    Get all issue groups for a specific repository.

    Args:
        access_token (str): OAuth2 access token for authentication.
        repo_id (str): Repository ID.

    Returns:
        List[Dict[str, Any]]: List of issue groups.
    """
    url = "https://app.aikido.dev/api/public/v1/open-issue-groups"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params = {"filter_code_repo_id": repo_id}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Failed to retrieve issue groups: {response.status_code} - {response.text}"
        )


def get_issue_group_ids(issue_groups: List[Dict[str, Any]]) -> str:

    issue_group_ids = []
    for issue_group in issue_groups:
        issue_group_ids.append(issue_group["id"])
    return issue_group_ids


def export_issue_details(args: tuple[str, str, str]) -> List[Dict[str, Any]]:
    """
    Export all issues for a specific repository from s API.

    Args:
        access_token (str): The OAuth2 access token for authentication.
        repository_id (str): The unique identifier of the code repository.
        format (str): The desired format of the export ('json' or 'csv'). Defaults to 'json'.

    Returns:
        Union[dict, str]: The issues data in JSON format as a dictionary or CSV format as a string.

    Raises:
        Exception: If the API request fails or returns an error.
    """
    access_token, repository_id, issue_group_id = args

    # s endpoint for exporting all issues
    url = "https://app.aikido.dev/api/public/v1/issues/export"

    # Set up the headers with the access token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Set up the query parameters with the repository ID and desired format
    params = {
        "filter_code_repo_id": repository_id,
        "filter_issue_group_id": issue_group_id,
        "filter_status": "open",
    }

    # Make the GET request to the API
    response = requests.get(url, headers=headers, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        return {issue_group_id: response.json()}

    else:
        # Raise an exception with the error details
        raise Exception(
            f"Failed to export issues: {response.status_code} - {response.text}"
        )


def export_issue_details_wrapper(
    access_token: str, repo_id: str, issue_group_id_list: Dict[str, Any]
) -> List[Dict[str, Any]]:
    results = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(export_issue_details, (access_token, repo_id, issue_id))
            for issue_id in issue_group_id_list
        ]
        for future in futures:
            results.update(future.result())

    return results


def merge_issue_details_with_issue_groups(
    issue_groups: List[Dict[str, Any]], issue_details: Dict[str, Any]
) -> List[Dict[str, Any]]:

    issue_groups_dict = {}

    for issues in issue_groups:

        issue_groups_dict.update({issues.get("id"): issues})

    for issue_group_id, issue_list in issue_details.items():

        issue_group: Dict[str, Any] = issue_groups_dict.get(issue_group_id, {})

        issue_group.update({"issue_list": issue_list})

        issue_groups_dict.update({issue_group_id: issue_group})

    with open("merged_issue_group.py", "w") as f:
        f.write(str(issue_groups_dict))

    return issue_groups_dict


def filter_high_and_critical(merged_issue_list: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out issues that are not high or critical severity.

    Args:
        issue_list (List[Dict[str, Any]]): List of issues.

    Returns:
        List[Dict[str, Any]]: Filtered list of high and critical severity issues.
    """
    with open("issues.json", "w") as f:
        f.write(str(merged_issue_list))

    filtered_issue_groups = {}
    for issue_group_id, issue_group in merged_issue_list.items():
        if issue_group.get("severity") in ["high", "critical"]:
            filtered_issue_groups.update({issue_group_id: issue_group})

    return filtered_issue_groups


def get_high_and_critical_issues(client_id, client_secret, repo_name) -> Dict[str, Any]:

    try:
        print("Getting OAuth token...")
        oauth_token = get_oauth_token(client_id, client_secret)

        print("Getting code repositories...")
        repos = get_code_repositories(oauth_token)

        repo_id = get_repo_id(repos, repo_name)

        print(f"Repository ID for {repo_name}: {repo_id}")

        print("Getting all issue groups...")
        issue_groups = get_open_issue_groups(oauth_token, repo_id=repo_id)

        print(f"Number of issue groups for {repo_name}: {len(issue_groups)}")

        issue_group_ids = get_issue_group_ids(issue_groups)

        print("Getting issue details...")
        issue_details = export_issue_details_wrapper(
            oauth_token, repo_id, issue_group_ids
        )

        merged_issues = merge_issue_details_with_issue_groups(
            issue_groups, issue_details
        )

        print("Filtering high and critical issues...")

        high_and_critical_issues = filter_high_and_critical(merged_issues)

        print(
            f"Number of high and critical issues for {repo_name}: {len(high_and_critical_issues)}"
        )

        return high_and_critical_issues, repo_id

    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)


def generate_table(high_and_critical_issues: Dict[str, Any], repo_id: str) -> str:

    table = "|Issue description|File location or affected package|Severity|Link|\n|---|---|---|---|\n"

    if len(high_and_critical_issues) == 0:
        return f"\n# SAST scan results\nNo high or critical issues found in codebase ✅"

    for issue_group_id, issue_group in high_and_critical_issues.items():

        description = issue_group.get("description", "")

        issue_type = issue_group.get("type", "").replace("_", " ").title()
        if issue_type == "leaked_secret":
            continue

        affected_files = []

        file_list = ""
        file_count = 0
        for issue in issue_group.get("issue_list", {}):

            if description == "" or description == None:
                description = issue.get("affected_package", "")

            affected_file = issue.get("affected_file", "")
            if affected_file == None or affected_file == "":
                attack_surface = issue.get("attack_surface", "")
                if attack_surface == "docker_container":
                    file_list += f"[Dockerfile]({project_url}/-/blob/{source_branch_name}/Dockerfile)"
                    break
                else:
                    affected_package = issue.get("affected_package")
                    if affected_package in file_list:
                        continue
                    file_list += f"Package: `{affected_package}`<br>"
                    continue

            file_list += f"[{affected_file}]({project_url}/-/blob/{source_branch_name}/{affected_file})"

            if file_count == 2:
                file_list += "<details><summary>view more files</summary>"
            file_count += 1

        if file_count >= 2:
            file_list += "</details>"

        if len(affected_files) == 0:
            affected_files = [""]

        severity = issue_group.get("severity")
        if severity == "critical":
            severity = "$`\textcolor{red}{\text{critical}}`$"
        elif severity == "high":
            severity = "$`\textcolor{orange}{\text{high}}`$"
        elif severity == "medium":
            severity = "$`\textcolor{yellow}{\text{medium}}`$"

        link = f"https://app.aikido.dev/repositories/{repo_id}?sidebarIssue={issue_group_id}"

        table += f"|{description}|{file_list}|{severity}|{link}|\n"

    final_table = f"\n# SAST scan results\n{len(high_and_critical_issues)} issues found in codebase❗\n<details><summary>SAST scan results</summary>\n\n{table}\n</details>"

    return final_table


def generate_issue_table(client_id, client_secret, repo_name):

    high_and_critical_issues, repo_id = get_high_and_critical_issues(
        client_id, client_secret, repo_name
    )

    return generate_table(high_and_critical_issues, repo_id)
