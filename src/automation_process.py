from .browser_manager import BrowserManager
from .notary_account import NotaryAccount
from .utils import *


class AutomationProcess:
    def __init__(self, user_data: dict):
        self.user_data = user_data
        self.notary = NotaryAccount(user_data.get("Email"))
        self.browser = BrowserManager(user_data)
        self.clients_data = self.notary.get_clients_data()

    def start_process(self):
        try:
            print("Starting notary automation process.")
            all_folders = self.notary.get_target_folders()

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
        fname, lname = split_name(full_name)
        dob, dod = get_dob_dod(self.clients_data, full_name)
        death_proof = self.notary.get_file_by_name(folder_id, ("acte de dece", "actes de dece"))
        mandat = self.notary.get_file_by_name(folder_id, ("mandat",))

        if all([fname, lname, is_good_size(death_proof), is_good_size(mandat), is_valid_date(dob), is_valid_date(dod)]):
            file1_path = self.notary.download_file(death_proof, "Acte de décès")
            file2_path = self.notary.download_file(mandat, "Mandat")

            if file1_path and file2_path:
                result = self.browser.perform_search(fname, lname, dob, dod, file1_path, file2_path)
                self.handle_search_result(result, folder_id, file1_path, file2_path)
        else:
            print("Missing data!")
            
    def handle_search_result(self, result, folder_id, file1_path, file2_path):
        if result[0] == 1:
            self.notary.move_folder(folder_id, self.notary.folder_id_23)
            if result[1]:
                recap_file = download_recap_file(result[1], self.browser.cookies)
                self.notary.upload_file(recap_file, folder_id)
            print("--> SUCCESSFUL <--")
        elif result[0] == -1:
            self.notary.move_folder(folder_id, self.notary.folder_id_25)
            print("--> NEGATIVE <--")
        else:
            print("--> ERROR <--")
        os.remove(file1_path)
        os.remove(file2_path)
