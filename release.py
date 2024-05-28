import os
from time import sleep
import requests


def delete_release_and_tag(headers, repo, release_id, tag):
    """Delete the release and its associated Git tag."""
    # Delete the release
    delete_release_url = f"https://api.github.com/repos/{repo}/releases/{release_id}"
    response = requests.delete(delete_release_url, headers=headers)
    if response.status_code == 204:
        print(f"Release {release_id} successfully deleted.")
        sleep(5)
    else:
        print(f"Failed to delete release: {response.json()}")
        return False

    # Delete the tag reference
    delete_tag_url = f"https://api.github.com/repos/{repo}/git/refs/tags/{tag}"
    response = requests.delete(delete_tag_url, headers=headers)
    if response.status_code == 204:
        print(f"Tag {tag} successfully deleted.")
        sleep(5)
    else:
        print(f"Failed to delete tag: {response.json()}")
        return False

    return True


def create_tag_and_release(headers, repo, tag, commit_sha, release_title, file_path):
    """Create a new tag and release, then upload the file."""
    # Create the tag
    tag_data = {
        "tag": tag,
        "message": "Release " + tag,
        "object": commit_sha,
        "type": "commit",
    }
    response = requests.post(
        f"https://api.github.com/repos/{repo}/git/tags", headers=headers, json=tag_data
    )
    if response.status_code == 201:
        print(f"Tag {tag} successfully created.")
        sleep(5)
    else:
        print(f"Failed to create tag: {response.json()}")
        return False

    # Create the release
    release_data = {
        "tag_name": tag,
        "name": release_title,
        "draft": False,
        "prerelease": False,
    }
    response = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=headers,
        json=release_data,
    )
    if response.status_code == 201:
        release_id = response.json()["id"]
        print(f"Release {release_id} successfully created.")
        sleep(5)
    else:
        print(f"Failed to create release: {response.json()}")
        return False

    # Upload the file to the release
    upload_url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={os.path.basename(file_path)}"
    with open(file_path, "rb") as file:
        headers["Content-Type"] = "application/octet-stream"
        response = requests.post(upload_url, headers=headers, data=file.read())
        if response.status_code in range(200, 300):
            print("Asset uploaded successfully")
            sleep(5)
            return True
        else:
            print(f"Failed to upload asset: {response.json()}")
            return False


def main():
    token = os.getenv("GITHUB_TOKEN")
    tag = os.getenv("RELEASE_TAG")
    commit_sha = os.getenv(
        "COMMIT_SHA"
    )  # This needs to be dynamically determined or passed in
    repo = os.getenv("REPO")
    repo_name = repo.split("/")[-1]
    file_path = f"output/{repo_name}.exe"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Fetch the release by tag
    response = requests.get(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}", headers=headers
    )
    if response.status_code == 200:
        release_id = response.json()["id"]
        delete_release_and_tag(headers, repo, release_id, tag)
    else:
        print(f"Failed to fetch release or release does not exist: {response.json()}")
    create_tag_and_release(headers, repo, tag, commit_sha, repo_name, file_path)


if __name__ == "__main__":
    main()
