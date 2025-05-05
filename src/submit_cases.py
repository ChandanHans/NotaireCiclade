import random
from .case_submission import CaseSubmissionFlow
from .ciclade_api_session import CicladeApiSession
from .notary_account import NotaryAccount
from .utils import *


class SubmitCases:
    def __init__(self, session:CicladeApiSession):
        self.session = session
        self.notary = NotaryAccount(session.user_email)
        self.clients_data = self.notary.get_clients_data()

    def start_process(self):
        try:
            print("----> Start CICLADE Submission <----")
            all_folders = self.notary.get_folders("2.2")
            if all_folders:
                for index, folder in enumerate(all_folders):
                    print("------------------------------------------------")
                    print(f"Processing folder {index + 1}/{len(all_folders)}: {folder['name']}")
                    try:
                        self.process_folder(folder)
                    except Exception as e:
                        print(f"Error : {e}")
                    print("------------------------------------------------")

            print("Task Completed Successfully")
        except Exception as e:
            print(f"An error occurred during the process: {e}")

    def process_folder(self, folder):
        folder_id = folder["id"]
        folder_name = folder["name"]
        full_name = remove_extra_spaces(folder_name).split("(")[0].strip()
        fname, lname = split_name(full_name)
        dob, dod = get_dob_dod(self.clients_data, folder_id)
        death_proof = self.notary.get_file_by_name(folder_id, ("acte de dece", "actes de dece"))
        mandat = self.notary.get_file_by_name(folder_id, ("mandat",))

        if all([fname, lname, is_good_size(death_proof), is_good_size(mandat), is_valid_date(dob), is_valid_date(dod)]):
            file1_path = self.notary.download_file(death_proof, "Acte de décès")
            file2_path = self.notary.download_file(mandat, "Mandat")

            if file1_path and file2_path:
                payload = {
                    "fname": fname,
                    "lname": lname,
                    "dob": dob,
                    "dod": dod,
                    "death_certificate": file1_path,
                    "mandat": file2_path,
                }

                case = CaseSubmissionFlow(self.session,payload)
                process_status = case.execute_workflow()
                if process_status or case.status:
                    try:
                        
                        recap_url = f"https://ciclade.caissedesdepots.fr/ciclade-service/api/telecharger-recapitulatif-soumission/{case.case_id}"
                        recap_file = self.session.download_file(recap_url, RECAP_FOLDER)
                        if recap_file:
                            self.notary.upload_file(recap_file, folder_id)
                            self.notary.move_folder(folder_id, "2.3" )
                            print("--> SUCCESSFUL <--")
                    except:
                        print("--> ERROR <--")
                    countdown(random.randint(200, 250))
                elif not case.status:
                    self.notary.move_folder(folder_id, "2.5")
                    print("--> NEGATIVE <--")
                os.remove(file1_path)
                os.remove(file2_path)
                time.sleep(3)
        else:
            print("Missing data!")
