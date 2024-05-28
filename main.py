from src.vcs import check_for_updates

check_for_updates()

import os
import re
import sys
import pickle
import tkinter as tk
from time import sleep
from threading import Thread
from datetime import datetime
from tkinter import filedialog

import gspread
import requests
from selenium import webdriver
from unidecode import unidecode
from cryptography.fernet import Fernet
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils import *
from src.constants import *
from src.print_loger import PrintLogger
from src.notary_account import NotaryAccount
from src.solve_captcha import get_captcha_result

sys.stdout = PrintLogger()
cipher_suite = Fernet(SETTING_KEY)

driver = None


def load_settings():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "rb") as f:
            encrypted_data = f.read()
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            return pickle.loads(decrypted_data)
    return {}


def save_settings():
    settings = {
        "email": email_var.get(),
        "password": password_var.get(),
        "owner": owner_var.get(),
        "iban": iban_var.get(),
        "bic": bic_var.get(),
        "pdfPath": pdf_file_path,
    }
    encrypted_data = cipher_suite.encrypt(pickle.dumps(settings))
    with open(SAVE_FILE, "wb") as f:
        f.write(encrypted_data)


def choose_file():
    global pdf_file_path
    filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    pdf_file_path = filepath
    pdf_var.set(os.path.basename(filepath))


def start_process():
    start_btn.config(state=tk.DISABLED)
    email = email_var.get()
    try:
        status_label.config(text="Getting information from Drive.", fg="#4CAF50")
        notary = NotaryAccount(email)
        all_clients_data = get_clients_data(notary.creds)
        status_label.config(text="Running...", fg="#4CAF50")
        driver = start_browser()
        all_folders = notary.get_target_folders()
        total_folder = len(all_folders)
        for index, folder in enumerate(all_folders):
            print("----------------------------------------------")
            folder_id: str = folder["id"]
            folder_name: str = folder["name"]
            status_label.config(
                text=f"{index}/{total_folder}\n\n{folder_name}", fg="#4CAF50"
            )
            full_name = remove_extra_spaces(folder_name).split("(")[0].strip()
            fname, lname = split_name(full_name)
            death_proof = notary.get_file_by_name(folder_id, "acte de dece")
            mandat = notary.get_file_by_name(folder_id, "mandat")
            dob, dod = get_dob_dod(all_clients_data, full_name)
            print(full_name, dob, dod)
            if all(
                [
                    fname,
                    lname,
                    is_good_size(death_proof),
                    is_good_size(mandat),
                    is_valid_date(dob),
                    is_valid_date(dod),
                ]
            ):
                file1_path = notary.download_file(death_proof)
                file2_path = notary.download_file(mandat)
                if file1_path and file2_path:
                    successful = new_search(
                        driver, fname, lname, dob, dod, file1_path, file2_path
                    )
                    try:
                        os.remove(file1_path)
                        os.remove(file2_path)
                    except:
                        pass
                    if successful == 1:
                        notary.move_folder(folder_id, notary.folder_id_2)
                        print("SUCCESSFUL")
                    elif successful == -1:
                        notary.move_folder(folder_id, notary.neg_folder_id)
                        print("NEGATIVE")
                    else:
                        print("ERROR")
            print("----------------------------------------------")

        status_label.config(text="Task Completed", fg="#4CAF50")
        close_driver()
    except requests.ConnectionError:
        status_label.config(text=f"No internet connection!", fg="#FF0000")
    except LookupError as e:
        status_label.config(
            text=f"Contact KLERO to add your information!", fg="#FF0000"
        )
    except Exception as e:
        status_label.config(text=f"Error: {e}", fg="#FF0000")
        print(e)
    finally:
        start_btn.config(state=tk.NORMAL)


def start_browser() -> webdriver.Chrome:
    global driver
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "autofill.credit_card_enabled": False,  # Disable Chrome's credit card autofill
            "autofill.enabled": False,  # Disable all autofill
        },
    )
    options.add_argument("--app=https://ciclade.caissedesdepots.fr/monespace")
    driver = webdriver.Chrome(options=options)
    try:
        click_element(driver, '//*[@id="didomi-notice-agree-button"]')
        sleep(3)
    except Exception:
        pass
    login(driver)
    return driver


def login(driver: webdriver.Chrome):
    send_keys_to_element(driver, '//*[@id="login"]', email_var.get())
    send_keys_to_element(driver, '//*[@id="f-login-passw"]', password_var.get())
    click_element(driver, '//button[@type="submit"]')
    wait_for_element(driver, '//*[@class="ttl-is-h1 ng-binding"]')


def click_element(driver: webdriver.Chrome, xpath):
    """Utility function to click on an element identified by xpath"""
    for _ in range(5):
        try:
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            return True
        except Exception:
            pass
    return False


def send_keys_to_element(driver: webdriver.Chrome, xpath, text):
    """Utility function to send text to an element identified by xpath"""
    for _ in range(5):
        try:
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.send_keys(text)
            return True
        except Exception:
            pass
    return False


def upload_to_element(driver: webdriver.Chrome, xpath, path):
    """Utility function to send text to an element identified by xpath"""
    for _ in range(5):
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            element.send_keys(path)
            return True
        except Exception:
            pass
    return False


def wait_for_element(driver, xpath, timeout=5):
    """Wait for an element to be visible."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return True
    except TimeoutException:
        return False


def solve_captcha(driver: webdriver.Chrome):
    while True:
        try:
            captcha_value = driver.execute_script(
                "return document.querySelector('#CAPTCHA').value;"
            )
            break
        except:
            pass
    while captcha_value == "":
        captcha_value = driver.execute_script(
            "return document.querySelector('#CAPTCHA').value;"
        )
        sleep(2)


def new_search(
    driver: webdriver.Chrome, fname, lname, dob, dod, temp_file1, temp_file2
) -> bool:
    try:
        driver.get("https://ciclade.caissedesdepots.fr/monespace/#/service/recherche")
        driver.refresh()

        click_element(driver, '//input[@id="f-s-p-death-yes"]')
        click_element(driver, '//*[@id="f-s-p-civilite-monsieur"]')
        send_keys_to_element(driver, '//input[@id="f-s-p-death-day"]', dob)
        send_keys_to_element(driver, '//input[@id="f-s-p-birth-day"]', dod)
        send_keys_to_element(driver, '//input[@id="f-s-p-surname1"]', fname)
        send_keys_to_element(driver, '//input[@id="f-s-p-name1"]', lname)
        click_element(driver, '//*[@id="f-s-p-nationality"]/option[@value="FRA"]')
        click_element(driver, '//*[@id="f-s-p-connu-no"]')

        try:
            captcha_image_url = (
                WebDriverWait(driver, 5)
                .until(EC.presence_of_element_located((By.ID, "captchaImg")))
                .get_attribute("src")
            )
            captcha_sound_url = captcha_image_url.replace("image", "sound")
            captcha_result = get_captcha_result(captcha_sound_url)
        except:
            return new_search(driver, fname, lname, dob, dod, temp_file1, temp_file2)
        send_keys_to_element(driver, '//*[@id="CAPTCHA"]', captcha_result)

        click_element(driver, '//*[@type="submit"]')
        click_element(driver, '//*[@ng-click="vm.rechercher()"]')

        sleep(2)

        if not wait_for_element(driver, '//*[text()="Résultat de votre recherche"]'):
            if wait_for_element(driver, '//h2[@id="modal-doublon-label"]'):
                return 0
            else:
                return new_search(
                    driver, fname, lname, dob, dod, temp_file1, temp_file2
                )

        if not click_element(driver, '//*[@id="FinalisationButton"]'):
            return -1

        # Step 1
        for _ in range(5):
            try:
                sleep(2)
                if not click_element(
                    driver, '//*[@id="positionDemandeur"]/option[@label="Notaire"]'
                ):
                    continue
                if not click_element(
                    driver, '//*[@id="f-s-p-paysBanque"]/option[@value="FR"]'
                ):
                    continue
                if not send_keys_to_element(
                    driver, '//*[@id="f-s-p-titulaire"]', owner_var.get()
                ):
                    continue
                if not send_keys_to_element(
                    driver, '//*[@id="f-s-p-iban"]', iban_var.get()
                ):
                    continue
                if not send_keys_to_element(
                    driver, '//*[@id="f-s-p-bic"]', bic_var.get()
                ):
                    continue
                if not upload_to_element(driver, '//*[@id="document"]', pdf_file_path):
                    continue
                if not click_element(driver, '//*[@ng-click="vm.poursuivre()"]'):
                    continue
                if wait_for_element(driver, '//*[@id="docAdditionnelNon"]'):
                    break
            except Exception as e:
                if _ == 4:
                    raise
                print("Error in Step 1")
                print(e)
                sleep(5)
                pass

        # Step 2
        for _ in range(5):
            try:
                sleep(2)
                if not click_element(driver, '//*[@id="docAdditionnelNon"]'):
                    continue
                if not upload_to_element(driver, '//*[@id="document-0"]', temp_file1):
                    continue
                if not upload_to_element(driver, '//*[@id="document-1"]', temp_file2):
                    continue
                if not click_element(driver, '//*[@ng-click="vm.poursuivre()"]'):
                    continue
                if wait_for_element(driver, '//*[@id="btnSoumission"]'):
                    break
            except Exception as e:
                if _ == 4:
                    raise
                print("Error in Step 2")
                print(e)
                sleep(5)
                driver.refresh()
                pass

        # Final submission
        click_element(driver, '//*[@id="btnSoumission"]')
        click_element(driver, '//*[@ng-click="vm.soumettreDemande()"]')
        click_element(driver, '//i[@class="fa fa-download"]/parent::a')

        sleep(1)
        return 1
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0


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


def is_good_size(file: dict[str, str]):
    try:
        size = round(int(file["size"]) / (1024 * 1024), 3)
        if size < 4:
            return True
        return False
    except:
        return False


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


def start():
    if owner_var and iban_var and bic_var and pdf_file_path:
        if os.path.exists(pdf_file_path):
            save_settings()
            thread = Thread(target=start_process, daemon=True)
            thread.start()
        else:
            status_label.config(text=f"Select RIB Pdf again!", fg="#FF0000")
    else:
        status_label.config(text=f"Fill all the information!", fg="#FF0000")


def close_driver():
    try:
        driver.quit()
    except Exception:
        pass

root = tk.Tk()
root.title("Notaire Ciclade")
root.iconbitmap(resource_path("images/icon.ico"))
root.geometry("600x500")
root.configure(bg="#2c2f33")
root.resizable(False, False)  # Fix window size

# Styling
BUTTON_STYLE = {
    "bg": "#3B3E44",
    "fg": "#ffffff",
    "activebackground": "#464B51",
    "border": "0",
    "font": ("Arial", 12, "bold"),
}

LABEL_STYLE = {"bg": "#2c2f33", "fg": "#ffffff", "font": ("Arial", 14, "bold")}

ENTRY_STYLE = {
    "bg": "#383c41",
    "fg": "#ffffff",
    "borderwidth": "1px",
    "relief": "solid",
    "width": 30,
    "font": ("Arial", 12),
}

STATUS_LABEL_STYLE = {"bg": "#2c2f33", "font": ("Arial", 12, "bold")}

# Load previous settings
settings = load_settings()
pdf_file_path = settings.get("pdfPath", "")

# Variables
email_var = tk.StringVar(value=settings.get("email", ""))
password_var = tk.StringVar(value=settings.get("password", ""))
owner_var = tk.StringVar(value=settings.get("owner", ""))
iban_var = tk.StringVar(value=settings.get("iban", ""))
bic_var = tk.StringVar(value=settings.get("bic", ""))
pdf_var = tk.StringVar(value=os.path.basename(pdf_file_path))

# Layout
rows = [
    ("Email:", email_var),
    ("Password:", password_var),
    ("Account owner:", owner_var),
    ("IBAN:", iban_var),
    ("BIC:", bic_var),
]

for idx, (text, var) in enumerate(rows, start=1):
    tk.Label(root, text=text, **LABEL_STYLE).grid(
        row=idx, column=0, sticky="w", padx=30, pady=5
    )
    if text == "Password:":
        # If this is the password field, use the show parameter to mask the input
        entry = tk.Entry(root, textvariable=var, show="*", **ENTRY_STYLE)
    else:
        entry = tk.Entry(root, textvariable=var, **ENTRY_STYLE)
    entry.grid(row=idx, column=1, padx=30, pady=5, sticky="e")

label = tk.Label(root, text="RIB PDF:", **LABEL_STYLE)
label.grid(row=len(rows) + 1, column=0, padx=30, pady=5, sticky="w")
pdf_frame = tk.Frame(root, bg="#2c2f33")
pdf_frame.grid(row=len(rows) + 1, column=1, padx=30, pady=5, sticky="e")
tk.Label(
    pdf_frame,
    textvariable=pdf_var,
    bg="#2c2f33",
    fg="#ffffff",
    width=33,
    anchor="e",
    font=("Arial", 12),
).pack(side=tk.LEFT)
tk.Button(pdf_frame, text="...", command=lambda: choose_file(), **BUTTON_STYLE).pack(
    side=tk.RIGHT
)


start_btn = tk.Button(root, text="Start Browser", command=start, **BUTTON_STYLE)
start_btn.grid(row=len(rows) + 5, column=0, columnspan=2, pady=10)
status_label = tk.Label(root, text="", **STATUS_LABEL_STYLE, wraplength=500, anchor="w")
status_label.grid(row=len(rows) + 6, column=0, columnspan=2, pady=10)

root.mainloop()
close_driver()
