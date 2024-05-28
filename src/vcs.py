import os
import sys
import requests
import datetime
import subprocess

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    return os.path.join(base_path, relative_path)

OWNER = "ChandanHans"
REPO_NAME = "NotaireCiclade"
EXE_NAME = "NotaireCiclade.exe"
RELEASE_TAG = "v1.0.0"
EXE_URL = f"https://github.com/{OWNER}/{REPO_NAME}/releases/download/{RELEASE_TAG}/NotaireCiclade.exe"
LOCAL_TIME_PATH = resource_path("time.txt")
UPDATER_EXE_PATH = resource_path("updater.exe")
EXE_PATH = sys.executable


def get_local_version_time():
    """Read the version date from the local version file."""
    with open(LOCAL_TIME_PATH, "r") as file:
        return datetime.datetime.strptime(file.read().strip(), "%Y-%m-%dT%H:%M:%SZ")


def get_latest_release_time():
    """Fetch the latest release time from the GitHub repository."""
    # Fetch the release by tag
    response = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO_NAME}/releases/tags/{RELEASE_TAG}"
    )
    release_info = response.json()

    required_asset = None
    for asset in release_info.get("assets", []):
        if asset["name"] == EXE_NAME:
            required_asset = asset
            break

    if not required_asset:
        print("No release information found.")
        return None

    release_time = datetime.datetime.strptime(
        required_asset["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
    )
    return release_time


def check_for_updates():
    """Check if an update is available based on the latest commit date."""
    print("Checking for updates...")
    if getattr(sys, "frozen", False):
        try:
            local_version_time = get_local_version_time()
        except:
            return
        remote_version_time = get_latest_release_time()

        if remote_version_time is None:
            return
        # Calculate the difference in time
        time_difference = remote_version_time - local_version_time
        # Check if the difference is greater than 2 minutes
        if time_difference > datetime.timedelta(minutes=2):
            try:
                subprocess.Popen([UPDATER_EXE_PATH, EXE_PATH, EXE_URL])
            except:
                input("ERROR : Contact Chandan")
            sys.exit()
