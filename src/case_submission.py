import requests

from .ciclade_api_session import CicladeApiSession


class CaseSubmissionFlow:
    def __init__(self, session: CicladeApiSession, payload: dict):
        self.session = session
        self.payload = payload
        self.case_full_name = f"{payload['lname']} {payload['fname']}"
        self.case_id = self.get_case_id()
        self.document_id = None  # Will be set if needed
        self.status = 0

    def get_case_id(self):
        """Fetch an existing open case if it matches."""
        try:
            response = self.session.get(
                "https://ciclade.caissedesdepots.fr/ciclade-service/api/liste-demandes"
            )
            if response.status_code == 200:
                for case in response.json().get("other", []):
                    if (
                        case.get("intituleDemande") == self.case_full_name
                        and case.get("statut") != "SUPPRIMEE"
                    ):
                        return case.get("idDemande")
        except requests.RequestException as e:
            print(f"!!! Error fetching case list: {e}")
        return None

    def get_document_id(self):
        """Extract RBI ID from a response."""
        response = self.session.get(
            f"https://ciclade.caissedesdepots.fr/ciclade-service/api/document-paiement-en-attente/{self.case_id}"
        )
        response_json = response.json()
        result = response_json["other"]
        self.document_id = result["idDocument"]
        return self.document_id

    def create_case(self):
        """Step 1: Create a new case if none exists."""
        print("Step 1:")

        for _ in range(10):  # Retry up to 5 times for invalid CAPTCHA
            payload = {
                "radioDeces": "true",
                "dateDeces": self.payload["dod"],
                "civilite": "MONSIEUR",
                "nom": self.payload["lname"],
                "prenom": self.payload["fname"],
                "dateNaissance": self.payload["dob"],
                "codeNationalite": "FRA",
                "validationCaptcha": self.session.get_captcha(),
            }
            try:
                response = self.session.post(
                    "https://ciclade.caissedesdepots.fr/ciclade-service/api/creer-demande",
                    json=payload,
                )

                if response.status_code == 201:
                    self.case_id = response.json()["other"]["idDemande"]
                    print(f"--- Case created with ID {self.case_id}.")
                    self.status = True
                    return True
                elif response.status_code == 412:
                    print("--- This case was already submitted.")
                    self.status = True
                    return False
                elif response.status_code == 400:
                    print("--- Invalid CAPTCHA. Retrying...")
                    self.session.refresh_captcha()
                elif response.status_code == 404:
                    print("--- No results found. Cannot create case.")
                    self.status = False
                    return False
                else:
                    print(f"Unexpected error: {response.status_code}")
                    self.status = False
                    return False

            except requests.RequestException as e:
                print(f"!!! Request error while creating case: {e}")
                return False

        print("!!! Failed to create case after multiple attempts.")
        return False

    def my_request(self):
        """Step 2: Submit initial data and RIB info."""
        print(f"Step 2:")
        if not self.case_id:
            print("!!! Cannot submit request. No case ID.")
            return False

        self.get_document_id()

        try:
            # Example: Step 2 submission
            self.session.post(
                "https://ciclade.caissedesdepots.fr/ciclade-service/api/poursuivre-etape1",
                json={
                    "idDemande": self.case_id,
                    "intituleDemande": self.case_full_name,
                    "codePosDemandeur": "NOTAIRE",
                },
            )

            # RIB Document Upload (if needed)
            with open(self.session.rbi_path, "rb") as file_data:
                rib_response = self.session.post(
                    f"https://ciclade.caissedesdepots.fr/ciclade-service/api/modifier-document-rib"
                    f"?idDocument={self.document_id}",
                    files={"file": file_data},
                )
                if rib_response.status_code == 201:
                    # Save bank details
                    self.session.put(
                        "https://ciclade.caissedesdepots.fr/ciclade-service/api/infos-bancaires-enregistrer/",
                        json={
                            "idDocument": self.document_id,
                            "codePaysBanque": "FR",
                            "titulaire": self.session.owner_name,
                            "bic": self.session.ibc,
                            "iban": self.session.iban,
                            "adresse": self.session.user_info.get("adresse", ""),
                            "codePostal": self.session.user_info.get("codePostal", ""),
                            "codePays": "FR",
                            "ville": self.session.user_info.get("ville", "")
                        },
                    )
                    print("--- RIB updated.")
                    return True
                else:
                    print(f"!!! Error uploading RIB.")
                    return False
        except (IOError, requests.RequestException) as e:
            print(f"!!! Error in step 2: {e}")
            return False

        return True

    def supporting_documents(self):
        """Step 3: Upload supporting docs."""
        print("Step 3:")
        if not self.case_id:
            print("!!! No case ID. Cannot upload documents.")
            return False

        print("--- Uploading documents.")
        try:
            # Death certificate
            with open(self.payload["death_certificate"], "rb") as file_data:
                self.session.post(
                    f"https://ciclade.caissedesdepots.fr/ciclade-service/api/creer-document"
                    f"?fileFamille=DOCUMENT_JUSTIFICATIF_DE_DECES&idDemande={self.case_id}",
                    files={"file": file_data},
                )

            # Mandat
            with open(self.payload["mandat"], "rb") as file_data:
                self.session.post(
                    f"https://ciclade.caissedesdepots.fr/ciclade-service/api/creer-document"
                    f"?fileFamille=MANDAT&idDemande={self.case_id}",
                    files={"file": file_data},
                )

            # Confirm step 2
            self.session.put(
                f"https://ciclade.caissedesdepots.fr/ciclade-service/api/demande/{self.case_id}/validation-etape2",
                json={"idDemande": self.case_id, "topInfosDocAdditionnel": False},
            )
            print("--- Documents uploaded.")
            return True
        except (IOError, requests.RequestException) as e:
            print(f"!!! Error uploading documents: {e}")
            return False

    def finalize_submission(self):
        """Step 4: Finalize the case submission."""
        print("Step 3:")
        print("--- Final submission.")
        try:
            response = self.session.post(
                f"https://ciclade.caissedesdepots.fr/ciclade-service/api/finalize/{self.case_id}"
            )
            if response.status_code == 200:
                print("--- Submission finalized.")
                return True
            else:
                print(f"!!! Failed finalization. Status code: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"!!! Error finalizing submission: {e}")
            return False

    def execute_workflow(self):
        """Execute the entire workflow (all steps)."""
        if not self.create_case():
            if self.status:
                print("--- Using existing case.")
            else:
                return False

        if not self.my_request():
            print("!!! Step 2 failed.")
            return False

        if not self.supporting_documents():
            print("!!! Step 3 failed.")
            return False

        # Uncomment to finalize automatically:
        # if not self.finalize_submission():
        #     print("!!! Step 4 failed.")
        #     return False

        print("Workflow completed.")
        return True
