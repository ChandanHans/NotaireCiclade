import logging
import requests
import json
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

class CicladeApiSession(requests.Session):
    SESSION_FILE = "session.json"
    LOGIN_URL = "https://ciclade.caissedesdepots.fr/ciclade-service/api/authentification"
    VERIFICATION_URL = "https://ciclade.caissedesdepots.fr/ciclade-service/api/double-authentification"
    CONFIRMATION_URL = "https://ciclade.caissedesdepots.fr/ciclade-service/api/account"
    CAPTCHA_IMAGE_URL = "https://ciclade.caissedesdepots.fr/ciclade-service/api/simple-captcha-endpoint?get=image&c=alphanumerique6to9LightCaptchaFR"
    CAPTCHA_SOUND_URL = "https://ciclade.caissedesdepots.fr/ciclade-service/api/simple-captcha-endpoint-sound?get=sound&c=alphanumerique6to9LightCaptchaFR&t="

    def __init__(self, user_data):
        super().__init__()
        self.user_email = user_data["Email"]
        self.password = user_data["Password"]
        self.owner_name = user_data["Account owner"]
        self.iban = user_data[ "IBAN"]
        self.ibc = user_data["BIC"]
        self.rbi_path = user_data["RBI Pdf"]
        self.gpt_client = OpenAI(api_key=os.environ["GPT_KEY"])
        self.token = None
        self.captcha = None

        self.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        })

        # Load session if it exists
        self.load_session()

        # Check if user info is available
        self.user_info = self.get_user_info()


    def get_user_info(self):
        for _ in range(5): 
            try:
                response = self.get("https://ciclade.caissedesdepots.fr/ciclade-service/api/account/account-detail")
                return response.json()["other"]
            except requests.RequestException as e:
                logger.error(f"Error fetching user info: {e}")

    def save_session(self):
        with open(self.SESSION_FILE, "w") as file:
            json.dump({"cookies": self.cookies.get_dict(), "token": self.token}, file)

    def load_session(self):
        if os.path.exists(self.SESSION_FILE):
            with open(self.SESSION_FILE, "r") as file:
                data = json.load(file)
                self.cookies.update(data.get("cookies", {}))
                self.token = data.get("token")
                if self.token:
                    self.headers.update({"x-csrf-token": self.token})

    def authenticate(self):
        print("Authenticating...")
        payload = {"login": self.user_email, "password": self.password}
        try:
            response = self.post(self.LOGIN_URL, params=payload)
            response_data = response.json()
        except requests.RequestException as e:
            logger.error(f"Authentication request error: {e}")
            print("Network error during authentication.")
            return False

        if response_data.get("key") != "authent.authorized":
            print("Authentication failed.")
            return False

        self.token = response_data["other"]["token"]
        self.headers.update({"x-csrf-token": self.token})
        verification_required = response_data["other"].get("displayDoubleAuthentification", False)

        if verification_required:
            print("Verification code sent. Please check your email.")
            verification_code = input("Enter verification code: ")
            verification_payload = {
                "codeMfa": verification_code,
                "trustedTerminal": True
            }
            try:
                verification_response = self.post(self.VERIFICATION_URL, json=verification_payload)
                if verification_response.status_code == 200:
                    print("Verification successful.")
                    self.save_session()
                    return True
                else:
                    print("Invalid verification code.")
                    return False
            except requests.RequestException as e:
                logger.error(f"Verification request error: {e}")
                print("Network error during verification.")
                return False
        else:
            print("Authenticated successfully.")
            self.save_session()
            return True

    def confirm_account(self):
        # Example of how to confirm account if needed
        headers = {"x-csrf-token": self.token}
        while True:
            try:
                response = self.get(self.CONFIRMATION_URL, headers=headers)
                if response.status_code == 200:
                    print("Account confirmed.")
                    return True
                else:
                    print("Re-authenticating...")
                    if not self.authenticate():
                        return False
            except requests.RequestException as e:
                logger.error(f"Error confirming account: {e}")
                return False

    def refresh_captcha(self):
        print("Retrieving CAPTCHA...")
        try:
            response = self.get(self.CAPTCHA_IMAGE_URL)
            if response.status_code == 200:
                captcha_data = response.json()
                uuid = captcha_data["uuid"]
                sound_url = f"{self.CAPTCHA_SOUND_URL}{uuid}"

                sound_response = self.get(sound_url)
                with open("captcha.wav", "wb") as f:
                    f.write(sound_response.content)

                # Use Whisper through openai to transcribe
                with open("captcha.wav", "rb") as audio_file:
                    transcription = self.gpt_client.audio.transcriptions.create(
                        model="whisper-1", file=audio_file, language="fr"
                    )

                # Remove non-alphanumeric chars
                captcha_text = "".join(char for char in transcription.text if char.isalnum())

                self.captcha = {"id": uuid, "code": captcha_text}
                print("CAPTCHA solved.")
                return self.captcha
        except requests.RequestException as e:
            logger.error(f"Error refreshing CAPTCHA: {e}")

        logger.error("Failed to get CAPTCHA.")
        return None

    def get_captcha(self):
        # Return existing or refresh if needed
        if not self.captcha:
            return "self.refresh_captcha()"
        return self.captcha

    def download_file(self, download_url, target_folder):
        response = self.get(download_url)
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