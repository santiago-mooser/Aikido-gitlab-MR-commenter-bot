import requests


def add_note_to_mr(
    gitlab_url: str, access_token: str, project_id: str, mr_iid: str, body: str
) -> dict | None:
    """
    Adds or updates a note to a GitLab merge request.
    If an existing note from this bot is found, the note is updated;
    otherwise, a new note is created. Uses the specified private token for
    authentication.

    Args:
        gitlab_url (str): The URL of the GitLab instance (with or without "https://").
        access_token (str): The private or personal access token for GitLab.
        project_id (str): The ID or slug of the GitLab project containing the merge request.
        mr_iid (str): The IID (internal ID) of the merge request to which the note will be added or updated.
        body (str): The text content of the note to be added or updated.

    Returns:
        dict or None: The JSON response from the GitLab API if a note is successfully added or updated;
        otherwise, None if the operation fails.
    """

    note_id = mr_already_has_note(gitlab_url, access_token, project_id, mr_iid)
    if note_id:
        # update note instead
        update_note(gitlab_url, access_token, project_id, mr_iid, note_id, body)
        print("Updated note.")
        return

    print("No note found. Adding a new one.")

    if ":" in access_token:
        access_token = access_token.split(":")[1]
    headers = {
        "Private_Token": access_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if "https://" not in gitlab_url:
        gitlab_url = f"https://{gitlab_url}"
    url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"

    data = {"body": body}
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Failed to add note to merge request - {url} {response.reason}")
        return None


def mr_already_has_note(
    gitlab_url: str, access_token: str, project_id: str, mr_iid: str
) -> int:
    """
    Checks if a GitLab merge request already contains a note with a specific text.
    This function retrieves the notes of a merge request from a GitLab instance
    and searches for a note that includes the substring "Security tooling scan results".
    If such a note is found, the note's ID is returned; if not or if the request fails,
    False is returned.

    Args:
        gitlab_url (str):
            The base URL of the GitLab instance, e.g., "https://gitlab.com".
        access_token (str):
            The private token used for authenticating with the GitLab API. If the token
            includes a "Private_Token:" prefix, it will be automatically removed.
        project_id (str):
            The ID (or URL-encoded path) of the GitLab project containing the merge request.
        mr_iid (str):
            The internal reference ID of the merge request.

    Returns:
        int or bool:
            The note ID if a matching note is found, or False otherwise.
    """

    # Get all notes for the MR
    if ":" in access_token:
        access_token = access_token.split(":")[1]
    headers = {"Private_Token": access_token, "Content-Type": "application/json"}
    url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        notes = response.json()

        for note in notes:
            if "Security tooling scan results" in note["body"]:
                return note["id"]
        return False
    else:
        print(f"Failed to get notes for merge request - {url} {response.reason}")
        return False


def update_note(
    gitlab_url: str,
    access_token: str,
    project_id: str,
    mr_iid: str,
    note_id: str,
    body: str,
) -> int:
    """
    Updates an existing note in a GitLab merge request.

    Args:
        gitlab_url (str): The base URL of the GitLab instance.
        access_token (str): A string token used to authenticate the request.
        project_id (str): The ID of the GitLab project containing the merge request.
        mr_iid (str): The IID (internal ID) of the merge request.
        note_id (str): The ID of the note to be updated.
        body (str): The updated content of the note.

    Returns:
        dict or None: The updated note data if the request is successful, otherwise None.
    """

    if ":" in access_token:
        access_token = access_token.split(":")[1]
    headers = {
        "Private_Token": access_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes/{note_id}"
    data = {"body": body}
    response = requests.put(url, data=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to update note for merge request - {url} {response.reason}")
        return None
