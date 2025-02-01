from .ciclade_api_session import CicladeApiSession
from .notary_account import NotaryAccount
from .utils import *


class UploadFiles:
    def __init__(self, session:CicladeApiSession):
        self.session = session
        self.notary = NotaryAccount(session.user_email)
        self.clients_data = self.notary.get_clients_data()
        self.all_case = self.get_all_cases()
        
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
    
    def process_folder(self, folder):
        folder_id = folder["id"]
        folder_name = folder["name"]
        full_name = remove_extra_spaces(folder_name).split("(")[0].strip()
        for case in self.all_case:
            if remove_extra_spaces(case["intituleDemande"]) == full_name:
                if case["statut"] == "PAIEMENT_EFFECTUE":
                    print("PAIEMENT_EFFECTUE")
                    payment_file_urls = self.get_payment_files(case["idDemande"])

                    for url in payment_file_urls:
                        has_paiement_file = True
                        file_path = self.download_file(url, PAYMENT_FOLDER)
                        file_name = os.path.basename(file_path)
                        exist = self.notary.get_file_by_name(folder_id,[file_name])
                        if not exist:
                            print(f"Uploading - {file_name}")
                            self.notary.upload_file(file_path, folder_id)
                        else:
                            print(f"Already Uploaded - {file_name}")
                    if has_paiement_file:
                        self.notary.move_folder(folder_id, "2.4" )
                
                elif case["statut"] == "REJETEE":
                    print("REJETEE")
                    self.notary.move_folder(folder_id, "2.5" )

    def get_all_cases(self):
        response = self.session.get("https://ciclade.caissedesdepots.fr/ciclade-service/api/liste-demandes")
        result : dict = response.json()
        return result.get("other",[])
    
    def get_payment_files(self, id):
        response = self.session.get(f"https://ciclade.caissedesdepots.fr/ciclade-service/api/recapitulatif-demande/{id}")
        result : dict = response.json()
        payment_files = []
        if result.get("other",[]):
            files = result["other"]["documentATelechargerLst"]
            for file in files:
                if file["type"] == "JUSTIF_PAIEMENT":
                    file_id = file["idDocJustificatif"]
                    url = f"https://ciclade.caissedesdepots.fr/ciclade-service/api/telecharger-justificatif-paiement/{id}/{file_id}"
                    payment_files.append(url)
        return payment_files
        
        
    def download_file(self, download_url, target_folder):
        response = self.session.get(download_url)
        content_disposition = response.headers.get("Content-Disposition")
        file_name = None
        if content_disposition:
            parts = content_disposition.split(";")
            for part in parts:
                if "filename=" in part:
                    file_name = part.split("=")[1].strip('"')
        if file_name:
            file_path = f"{target_folder}/{file_name}"
            with open(file_path, "wb") as file:
                file.write(response.content)
            full_path = os.path.join(os.getcwd(), file_path)
            return full_path