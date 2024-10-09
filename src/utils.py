from datetime import datetime
import os
import pickle
import re
import sys
import time
import os
import base64
import pickle
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from tkinter import Tk, filedialog
import gspread
import requests
from unidecode import unidecode

from .constants import *
from cryptography.fernet import Fernet

import msvcrt
import sys

def masked_input(prompt="Password: "):
    password = ''
    sys.stdout.write(prompt)
    sys.stdout.flush()

    while True:
        char = msvcrt.getch()

        if char in (b'\r', b'\n'):  # Enter key is pressed
            break
        elif char == b'\x08':  # Backspace key is pressed
            if len(password) > 0:
                password = password[:-1]
                sys.stdout.write('\b \b')  # Erase the last '*'
                sys.stdout.flush()
        else:
            password += char.decode('utf-8')
            sys.stdout.write('*')
            sys.stdout.flush()

    sys.stdout.write('\n')
    return password


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    return os.path.join(base_path, relative_path)


def remove_extra_spaces(text):
    # Use regular expression to replace multiple spaces with a single space
    return re.sub(r"\s+", " ", text)

def execute_with_retry(request, retries=5, initial_delay=1):
    """
    Execute a Google API request with retry logic and exponential backoff.
    
    :param request: The API request to execute.
    :param retries: The number of retries.
    :param initial_delay: Initial delay for exponential backoff.
    :return: The response from the request if successful.
    """
    delay = initial_delay
    for attempt in range(retries):
        try:
            return request.execute()
        except Exception as e:
            print(f"Error {e}\nRetrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    raise Exception(f"Max retries reached for request: {request.uri}")

# Function to encrypt the user data using the same salt and password
def encrypt_user_data(user_data: dict, derived_key: bytes):
    cipher = Fernet(derived_key)
    encrypted_data = cipher.encrypt(pickle.dumps(user_data))

    with open(USER_DATA_FILE, 'wb') as file:
        file.write(encrypted_data)
        
# Function to load saved and encrypted user data if it exists
def load_saved_data(derived_key: bytes):
    try:
        with open(USER_DATA_FILE, 'rb') as file:
            encrypted_data = file.read()

        # Decrypt the data using the derived key
        cipher = Fernet(derived_key)
        decrypted_data = cipher.decrypt(encrypted_data)

        # Deserialize the decrypted data
        data = pickle.loads(decrypted_data)
        # Check if the RBI Pdf file path exists
        if not os.path.isfile(data.get("RBI Pdf", "")):
            print("The RBI Pdf file path does not exist. Please select a valid file.")
            data["RBI Pdf"] = get_valid_file_path()

        return data

    except FileNotFoundError:
        return None
    except (pickle.UnpicklingError, ValueError):
        print("Error: Failed to decode the user data. It might be corrupted or tampered with.")
        return None
    except Exception as e:
        return None
    
# Function to get a valid file path using a file dialog and ensure the dialog is on top
def get_valid_file_path():
    root = Tk()  # Create a temporary root window
    root.withdraw()  # Hide the root window
    root.attributes('-topmost', True)  # Ensure the dialog appears on top

    file_path = None
    while not file_path or not os.path.isfile(file_path):
        file_path = filedialog.askopenfilename(title="Select a file", parent=root)
        if not os.path.isfile(file_path):
            print("Invalid file path selected. Please try again.")

    root.destroy()  # Destroy the temporary root window once the file is selected
    return file_path

# Function to get user input
def get_user_input():
    email_var = input("Email: ")
    password_var = masked_input("Password: ")
    owner_var = input("Account owner: ")
    iban_var = input("IBAN: ")
    bic_var = input("BIC: ")

    # Prompt for the RBI Pdf file with file validation
    print("Please select the RBI Pdf file:")
    rbi_path = get_valid_file_path()

    return {
        "Email": email_var,
        "Password": password_var,
        "Account owner": owner_var,
        "IBAN": iban_var,
        "BIC": bic_var,
        "RBI Pdf": rbi_path
    }
    
# Function to load the saved derived key if it exists
def load_derived_key():
    try:
        with open(KLERO_KEY_FILE, 'rb') as file:
            return file.read()
    except FileNotFoundError:
        return None

# Function to save the derived key for future use
def save_derived_key(derived_key: bytes):
    with open(KLERO_KEY_FILE, 'wb') as file:
        file.write(derived_key)



# Function to decrypt and load environment variables from the encrypted file into os.environ
def load_env_from_encrypted_file(derived_key: bytes, encrypted_file_path: str):
    try:
        with open(encrypted_file_path, 'rb') as file:
            encrypted_data = file.read()    # Read the remaining encrypted data

        # Use Fernet to decrypt the data
        cipher = Fernet(derived_key)
        decrypted_data = cipher.decrypt(encrypted_data)

        # Load the decrypted data into os.environ
        for line in decrypted_data.decode().splitlines():
            key, value = line.split('=', 1)  # Split each line by the '=' character
            os.environ[key.strip()] = value.strip()

        return True
    except Exception as e:
        return False

    
# Function to derive a key from the password
def derive_key(password: str) -> bytes:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def is_valid_date(date_text):
    try:
        if datetime.strptime(date_text, "%d/%m/%Y") and re.match(
            r"^\d{2}/\d{2}/\d{4}$", date_text
        ):
            return True
        else:
            return False
    except Exception:
        return False
    
def is_good_size(file: dict[str, str]):
    try:
        size = round(int(file["size"]) / (1024 * 1024), 3)
        if size < 4:
            return True
        return False
    except:
        return False
    
def split_name(full_name: str):
    name_parts = full_name.split()
    last_name_parts = [part for part in name_parts if part.isupper()]
    first_name_parts = [part for part in name_parts if not part.isupper()]
    last_name = " ".join(last_name_parts)
    first_name = " ".join(first_name_parts)
    return first_name, last_name


def get_clients_data(creds):
    gc = gspread.authorize(creds)
    factures_sheet = gc.open_by_key(FACTURES_SHEET_ID)
    factures_worksheet = factures_sheet.get_worksheet(0)
    all_data = factures_worksheet.get_all_values()
    required_data = [
        (remove_extra_spaces(row[1]).strip(), row[2], row[3]) for row in all_data
    ]
    return required_data


def get_dob_dod(all_data: tuple[str, str, str], name: str):
    for row in all_data:
        if unidecode(row[0]).lower() == unidecode(name).lower():
            return row[1], row[2]
    return None, None

def download_recap_file(download_url, cookie):
    headers = {
        "Cookie": cookie,
    }
    response = requests.get(download_url, headers=headers)
    content_disposition = response.headers.get("Content-Disposition")
    file_name = None
    if content_disposition:
        parts = content_disposition.split(";")
        for part in parts:
            if "filename=" in part:
                file_name = part.split("=")[1].strip('"')
    if file_name:
        file_path = f"{RECAP_FOLDER}/{file_name}"
        with open(file_path, "wb") as file:
            file.write(response.content)
        full_path = os.path.join(os.getcwd(), file_path)
        return full_path
