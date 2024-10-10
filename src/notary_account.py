import io
import shutil
from typing import Dict, Tuple

import gspread
from unidecode import unidecode
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload,MediaFileUpload

from .constants import *
from .utils import *


class NotaryAccount:
    def __init__(self, email) -> None:
        self.email : str = email
        self.creds  : service_account.Credentials = self.get_credentials()
        self.drive_service = self.get_drive_service()
        self.folder_id_22, self.folder_id_23, self.folder_id_25 = self.get_folder_id()

    def get_credentials(self):
        scopes = ["https://www.googleapis.com/auth/drive"]
        credentials = service_account.Credentials.from_service_account_info(
            eval(os.environ["CREDS_JSON"]), scopes=scopes
        )
        return credentials

    def get_drive_service(self):
        drive_service = build("drive", "v3", credentials=self.creds, cache_discovery=False)
        return drive_service

    def get_folder_id(self) -> Tuple[str, str, str]:
        gc = gspread.authorize(self.creds)
        notary_sheet = gc.open_by_key(NOTARY_SHEET_ID)
        notary_worksheet = notary_sheet.get_worksheet(0)
        data : list[str]= notary_worksheet.get_all_values()
        
        header_row : list[str] = data[0]
        header_indices = {header.lower(): index for index, header in enumerate(header_row)}
        
        email_column = header_indices.get('email')
        folder_id_1_column = header_indices.get('2.2')
        folder_id_2_column = header_indices.get('2.3')
        folder_id_3_column = header_indices.get('2.5')
        
        for row in data[1:]:  # Skip the header row
            if row and row[email_column].lower() == self.email.lower():
                return row[folder_id_1_column], row[folder_id_2_column], row[folder_id_3_column]
        
        raise LookupError("User not found in database")

    def get_target_folders(self):
        query = f"'{self.folder_id_22}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        all_folders = []
        try:
            request = self.drive_service.files().list(
                q=query, spaces="drive", fields="files(id, name)"
            )

            while request is not None:
                response = execute_with_retry(request)
                folders = response.get("files", [])
                all_folders += folders
                request = self.drive_service.files().list_next(request, response)

        except Exception as e:
            print(f"An error occurred: {e}")
        return all_folders

    def get_files_in_folder(self, folder_id):
        try:
            # Use the list method from the Drive API to retrieve all files in the folder
            request = self.drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="files(id, name, size, mimeType)",
                )
            response = execute_with_retry(request)

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

    def download_file(self, file: Dict[str, str], own_file_name = None) -> str:
        # Maximum file name length (excluding extension)
        MAX_LENGTH = 45

        # Extract file name and extension
        file_name = file["name"]
        name, extension = os.path.splitext(file_name)

        # If the name exceeds the maximum allowed length, truncate it and add the extension back
        if len(name) > MAX_LENGTH:
            name = name[:MAX_LENGTH]

        truncated_file_name = f"{name}{extension}"

        file_path = f"{DOCUMENT_FOLDER}/{truncated_file_name}"
        full_path = os.path.join(os.getcwd(), file_path)

        request = self.drive_service.files().get_media(fileId=file["id"])
        fh = io.BytesIO()  # Using a file-like object for streaming download
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Once the download is complete, write the file to disk
        with open(full_path, "wb") as f:
            fh.seek(0)  # Move to the beginning of the file-like buffer
            f.write(fh.read())

        # Copy the file to a different location with a new name
        new_file_name = f"{own_file_name}{extension}"  # Define the new file name
        new_full_path = os.path.join(os.getcwd(), new_file_name)

        # Copy the file to the new location
        shutil.copy(full_path, new_full_path)

        return new_full_path

    def upload_file(self, file_path, folder_id):
        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id]
            }

            # Media file upload
            media = MediaFileUpload(file_path, resumable=True)

            # Create the file in the specified folder
            request = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            execute_with_retry(request)
        except Exception as e:
            print(f"Failed to upload file: {e}")
    
    def move_folder(self, folder_id, move_to):
        try:
            # Use the update method of the Drive service to move the folder
            request = self.drive_service.files().update(
                fileId=folder_id,
                addParents=move_to,
                removeParents=self.folder_id_22,
                fields="id, parents",
            )
            execute_with_retry(request)
        except Exception as e:
            print(f"Failed to move folder: {e}")

    def get_clients_data(self):
        gc = gspread.authorize(self.creds)
        factures_sheet = gc.open_by_key(FACTURES_SHEET_ID)
        factures_worksheet = factures_sheet.get_worksheet(0)
        all_data = factures_worksheet.get_all_values()
        required_data = [
            (remove_extra_spaces(row[1]).strip(), row[2], row[3]) for row in all_data
        ]
        return required_data