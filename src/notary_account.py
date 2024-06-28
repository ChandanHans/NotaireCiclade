import io
from typing import Dict, Tuple

import gspread
from unidecode import unidecode
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .constants import *
from .utils import *


class NotaryAccount:
    def __init__(self, email) -> None:
        self.email = email
        self.creds = self.get_credentials()
        self.drive_service = self.get_drive_service()
        self.folder_id_1, self.folder_id_2, self.neg_folder_id = self.get_folder_id()

    def get_credentials(self):
        scopes = ["https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(
            CREDS_JSON, scopes=scopes
        )
        return credentials

    def get_drive_service(self):
        drive_service = build("drive", "v3", credentials=self.creds)
        return drive_service

    def get_folder_id(self) -> Tuple[str, str, str]:
        gc = gspread.authorize(self.creds)
        notary_sheet = gc.open_by_key(NOTARY_SHEET_ID)
        notary_worksheet = notary_sheet.get_worksheet(0)
        data = notary_worksheet.get_all_values()
        for row in data:
            if row and row[1].lower() == self.email.lower():
                return row[2], row[3], row[4]
        raise LookupError("User not found in database")

    def get_target_folders(self):
        query = f"'{self.folder_id_1}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        all_folders = []
        try:
            request = self.drive_service.files().list(
                q=query, spaces="drive", fields="files(id, name)"
            )

            while request is not None:
                response = request.execute()
                folders = response.get("files", [])
                all_folders += folders
                request = self.drive_service.files().list_next(request, response)

        except Exception as e:
            print(f"An error occurred: {e}")
        return all_folders

    def get_files_in_folder(self, folder_id):
        try:
            # Use the list method from the Drive API to retrieve all files in the folder
            response = (
                self.drive_service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="files(id, name, size, mimeType)",
                )
                .execute()
            )

            file_list = response.get("files", [])
            
            # Define a mapping of MIME types to file extensions
            mime_to_extension = {
                'application/pdf': '.pdf',
                'image/jpeg': '.jpg',
                'image/png': '.png',
            }
            
            for file in file_list:
                # Check if the file name has an extension
                if '.' not in file['name']:
                    # Get the MIME type and find the corresponding extension
                    mime_type = file.get('mimeType')
                    extension = mime_to_extension.get(mime_type, '')
                    if extension:
                        # Update the file name with the proper extension
                        file['name'] += extension
            
            return file_list
        except Exception as e:
            print(f"An error occurred: {e}")
            return []


    def get_file_by_name(self, folder_id: str, name_list: tuple[str]) -> Dict[str, str]:
        try:
            file_list: dict[str, str] = self.get_files_in_folder(folder_id)
            if file_list:
                for file in file_list:
                    if any(unidecode(name.lower()) in unidecode(file["name"].lower()) for name in name_list):
                        return file
        except Exception as e:
            print(f"An error occurred: {e}")
        return {}

    def download_file(self, file: Dict[str, str]) -> str:

        request = self.drive_service.files().get_media(fileId=file["id"])
        fh = io.BytesIO()  # Using a file-like object for streaming download
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Once the download is complete, write the file to disk
        path = os.path.join(os.getcwd(), file["name"])
        with open(path, "wb") as f:
            fh.seek(0)  # Move to the beginning of the file-like buffer
            f.write(fh.read())

        return path

    def move_folder(self, folder_id, move_to):
        try:
            # Use the update method of the Drive service to move the folder
            self.drive_service.files().update(
                fileId=folder_id,
                addParents=move_to,
                removeParents=self.folder_id_1,
                fields="id, parents",
            ).execute()
        except Exception as e:
            print(f"Failed to move folder: {e}")
