from .browser_manager import BrowserManager
from .notary_account import NotaryAccount
from .utils import *


class UploadFiles:
    def __init__(self, user_data: dict):
        self.user_data = user_data
        self.notary = NotaryAccount(user_data.get("Email"))
        self.browser = BrowserManager(user_data)

    def start_process(self):
        try:
            print("----> Uploading CICLADE_Justif_paiement <----")
            all_folders = self.notary.get_folders("2.3")
            if all_folders:
                for index, folder in enumerate(all_folders):
                    print("------------------------------------------------")
                    print(f"Processing folder {index + 1}/{len(all_folders)}: {folder['name']}")
                    self.process_folder(folder)
                    print("------------------------------------------------")

            print("Task Completed Successfully")
        except Exception as e:
            print(f"An error occurred during the process: {e}")
        finally:
            self.browser.close_browser()

    def process_folder(self, folder):
        folder_id = folder["id"]
        folder_name = folder["name"]
        full_name = remove_extra_spaces(folder_name).split("(")[0].strip()
        result = self.browser.get_payment_files(full_name)
        if result[0] == 1:
            for link in result[1]:
                if "paiement" in link.lower():
                    file_path = self.browser.download_file(link, PAYMENT_FOLDER)
                    file_name = os.path.basename(file_path)
                    exist = self.notary.get_file_by_name(folder_id,[file_name])
                    if not exist:
                        print(f"Uploading - {file_name}")
                        self.notary.upload_file(file_path, folder_id)
                    else:
                        print(f"Already Uploaded - {file_name}")
            self.notary.move_folder(folder_id, "2.4" )
        
        if result[0] == -1:
            self.notary.move_folder(folder_id, "2.5" )
