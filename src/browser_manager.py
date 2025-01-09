import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from openai import OpenAI

from .solve_captcha import get_captcha_result

class BrowserManager:
    def __init__(self, user_data: dict):
        self.user_data = user_data
        self.driver = self.initialize_browser()
        self.login()
        self.cookies = self.get_cookie()
        self.gpt_client = OpenAI(api_key=os.environ["GPT_KEY"])
        
    def initialize_browser(self) -> webdriver.Firefox:
        profile_path = self.create_browser_profile()
        options = Options()
        options.add_argument("-profile")
        options.add_argument(profile_path)
        self.driver = webdriver.Firefox(options=options)
        self.driver.implicitly_wait(4)
        self.driver.get("https://ciclade.caissedesdepots.fr/monespace")
        return self.driver

    def create_browser_profile(self):
        profile_path = os.path.join(os.getcwd(), "firefox_profile")
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
            with webdriver.Firefox(options=Options()) as temp_driver:
                temp_driver.get("https://www.google.com")
            print("Profile created successfully.")
        return profile_path

    def login(self):
        print("--------->  Login")
        while True:
            self.enter_text_in_element('//*[@id="login"]', self.user_data.get("Email"))
            self.enter_text_in_element('//*[@id="f-login-passw"]', self.user_data.get("Password"))
            self.click_element('//button[@type="submit"]')
            time.sleep(1)
            if(self.wait_for_element('//*[@id="checkbox-mfa"]')):
                if(self.driver.find_element(By.XPATH, '//*[@id="checkbox-mfa"]').is_displayed()):
                    self.click_element('//*[@id="checkbox-mfa"]')
                    while (self.driver.find_element(By.XPATH, '//*[@id="checkbox-mfa"]').is_displayed()):
                        time.sleep(1)
            if self.wait_for_element('//*[@class="ttl-is-h1 ng-binding"]'):
                break
            self.driver.get("https://ciclade.caissedesdepots.fr/monespace")
    
    def get_cookie(self):
        self.driver.get("https://ciclade.caissedesdepots.fr/ciclade-service/api/account")
        cookies = self.driver.get_cookies()
        jsessionid_cookie = None
        for cookie in cookies:
            if cookie["name"] == "JSESSIONID":
                jsessionid_cookie = cookie["value"]
                break
        if jsessionid_cookie:
            return f"JSESSIONID={jsessionid_cookie}"
    
    def perform_search(self, fname: str, lname: str, dob: str, dod: str, file1_path: str, file2_path: str, attempt=0) -> tuple:
        """
        Performs a search operation in the browser for the given first name, last name, 
        date of birth, date of death, and associated files.

        Args:
            fname (str): First name of the individual.
            lname (str): Last name of the individual.
            dob (str): Date of birth.
            dod (str): Date of death.
            file1_path (str): Path to the first file.
            file2_path (str): Path to the second file.

        Returns:
            tuple: A tuple indicating the search result status and an optional download URL.
        """
        attempt += 1
        if attempt > 15:
            print("----------------------")
            print("Skip after 15 attempt")
            return (0, None)
        try:
            already_exist = False
            self.driver.get("https://ciclade.caissedesdepots.fr/monespace/#/service/mes-demandes")
            self.driver.refresh()
            self.enter_text_in_element('//div[@id="mes-demandes_filter"]//input', f"{lname} {fname}", show_error=False)

            if self.wait_for_element('//table[@id="mes-demandes"]/tbody/tr/td[6]'):
                status = self.driver.find_element(By.XPATH, '//table[@id="mes-demandes"]/tbody/tr/td[6]').get_attribute("innerText")
                if(status == "Finaliser"):
                    print("--------->  Finaliser")
                    self.click_element('//table[@id="mes-demandes"]/tbody/tr/td[6]/span/a')
                    if self.wait_for_element('//*[@id="positionDemandeur"]'):
                        already_exist = True
                if(status == "Consulter"):
                    print("--------->  Consulter")
                    self.click_element('//table[@id="mes-demandes"]/tbody/tr/td[6]/span/a')
                    download_url = None
                    if self.wait_for_element('//i[@class="fa fa-download"]/parent::a'):
                        download_url = self.driver.find_element(By.XPATH, '//i[@class="fa fa-download"]/parent::a').get_attribute("href")
                    time.sleep(1)
                    return (1, download_url)

            if not already_exist:
                print("--------->  New Case")
                self.driver.get("https://ciclade.caissedesdepots.fr/monespace/#/service/recherche")
                self.driver.refresh()
                self.click_element('//*[@id="recherche.estDecede-oui"]')
                self.enter_text_in_element('//*[@id="dateDeces"]', dod)
                self.click_element('//*[@id="recherche.civiliteListe-m"]')
                self.enter_text_in_element('//*[@id="nom"]', lname)
                self.enter_text_in_element('//*[@id="prenom"]', fname)
                self.enter_text_in_element('//*[@id="dateNaissance"]', dob)
                self.select_dropdown('//*[@id="codeNationalite"]', "1: FRA")

                toggle_button = self.driver.find_element(
                By.XPATH, '//*[@id="ngb-accordion-item-1-toggle"]'
            )
                button_status = toggle_button.get_attribute("aria-expanded")
                if button_status == "false":
                    self.click_element('//*[@id="ngb-accordion-item-1-toggle"]')
                self.click_element('//*[@id="recherche.produit.dispose-non"]')

                try:
                    captcha_image = self.driver.find_element(By.ID, "captchaImg").get_attribute(
                        "src"
                    )
                    captcha_result = get_captcha_result(self.gpt_client, captcha_image)
                except:
                    return self.perform_search(fname, lname, dob, dod, file1_path, file2_path, attempt)
                self.enter_text_in_element('//*[@id="CAPTCHA"]', captcha_result)

                self.click_element('//*[@id="boutonValider"]')  # submit

                self.click_element( '//*[@data-target="#confirmationModal"]')
                self.click_element( '//*[@id="boutonLancerModale"]')
                
                if not self.wait_for_element( '//*[text()="Résultat de votre recherche"]', timeout = 5):
                    return self.perform_search(fname, lname, dob, dod, file1_path, file2_path, attempt)

                if not self.click_element( '//*[@id="FinalisationButton"]'):
                    return (-1, None)

            # Step 1
            for i in range(5):
                print("--------->  Step 1")
                time.sleep(2)
                if self.wait_for_element( '//*[@id="positionDemandeur"]'):
                    self.select_dropdown(
                        '//*[@id="positionDemandeur"]', "string:NOTAIRE"
                    )
                    self.select_dropdown( '//*[@id="f-s-p-paysBanque"]', "FR")
                    self.enter_text_in_element(
                        '//*[@id="f-s-p-titulaire"]', self.user_data.get("Account owner")
                    )
                    if not (already_exist and self.wait_for_element( '//button[contains(text(),"Modifier")]')):
                        self.enter_text_in_element( '//*[@id="f-s-p-iban"]', self.user_data.get("IBAN"))
                        
                    self.enter_text_in_element( '//*[@id="f-s-p-bic"]', self.user_data.get("BIC"))
                    if self.wait_for_element( '//*[@id="document"]'):
                        self.upload_to_element( '//*[@id="document"]', self.user_data.get("RBI Pdf"))
                    self.click_element( '//*[@ng-click="vm.poursuivre()"]')
                    time.sleep(3)
                if self.wait_for_element( '//*[@id="docAdditionnelNon"]', 20):
                    break
                if i == 4:
                    raise
                print("Error in Step 1")
                time.sleep(2)
                self.driver.refresh()

            # Step 2
            for i in range(5):
                print("--------->  Step 2")
                time.sleep(2)
                if(already_exist):
                    while self.wait_for_element( '//button[contains(text(),"Supprimer")]'):
                        self.click_element('//button[contains(text(),"Supprimer")]')
                        
                if self.wait_for_element( '//*[@id="docAdditionnelNon"]'):
                    self.click_element( '//*[@id="docAdditionnelNon"]')
                    if self.wait_for_element( '//*[@id="document-0"]', 1):
                        self.upload_to_element( '//*[@id="document-0"]', file1_path)
                    if self.wait_for_element( '//*[@id="document-1"]', 1):
                        self.upload_to_element( '//*[@id="document-1"]', file2_path)
                    self.click_element( '//*[@ng-click="vm.poursuivre()"]')
                    time.sleep(3)
                if self.wait_for_element( '//*[@id="btnSoumission"]', 10):
                    break
                if i == 4:
                    raise
                print("Error in Step 2")
                time.sleep(2)
                self.driver.refresh()
                pass
            
            print("--------->  Final submission")
            # Final submission
            self.click_element( '//*[@id="btnSoumission"]')
            self.click_element( '//*[@ng-click="vm.soumettreDemande()"]')
            download_url = None
            if self.wait_for_element( '//i[@class="fa fa-download"]/parent::a'):
                download_url = self.driver.find_element(By.XPATH, '//i[@class="fa fa-download"]/parent::a').get_attribute("href")

            time.sleep(1)
            return (1, download_url)

        except Exception as e:
            print(f"An error occurred during search: {e}")
            return (0, None)

    def enter_search_details(self, fname: str, lname: str, dob: str, dod: str):
        """Helper method to enter search details in the form."""
        self.click_element('//*[@id="recherche.estDecede-oui"]')
        self.enter_text_in_element('//*[@id="dateDeces"]', dod)
        self.click_element('//*[@id="recherche.civiliteListe-m"]')
        self.enter_text_in_element('//*[@id="nom"]', lname)
        self.enter_text_in_element('//*[@id="prenom"]', fname)
        self.enter_text_in_element('//*[@id="dateNaissance"]', dob)
        self.select_dropdown('//*[@id="codeNationalite"]', "1: FRA")
        
        
    def solve_captcha(self) -> str:
        """Handles the captcha solving mechanism."""
        try:
            captcha_image_url = self.driver.find_element(By.ID, "captchaImg").get_attribute("src")
            return get_captcha_result(self.gpt_client, captcha_image_url)  # Assuming you have a function to solve captchas
        except Exception as e:
            print(f"Captcha solving failed: {e}")
            return ""
    
    def click_element(self, xpath, max_tries=5):
        for _ in range(max_tries):
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(1)
                element.click()
                return True
            except Exception as e:
                print(f"Error clicking element with XPath: {xpath}, Error: {e}")
        return False

    def enter_text_in_element(self, xpath, text, max_tries=5, show_error = True):
        for _ in range(max_tries):
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(1)
                element.clear()
                element.send_keys(text)
                return True
            except Exception as e:
                if show_error:
                    print(f"Error sending text to element with XPath: {xpath}, Error: {e}")
        return False

    def wait_for_element(self, xpath, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return True
        except Exception as e:
            print(f"Error waiting for element with XPath: {xpath}, Error: {e}")
            return False
        
    def select_dropdown(self, xpath, value):
        for _ in range(5):
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                time.sleep(1)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                dropdown = Select(element)
                dropdown.select_by_value(value)
                return True
            except Exception as e:
                print(f"XPATH : {xpath}")
                print(f"ERROR : {e}")
                pass
        return False
    
    def upload_to_element(self, xpath, path: str):
        for _ in range(5):
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                element.send_keys(path.replace("/", "\\"))
                return True
            except Exception as e:
                print(f"XPATH : {xpath}")
                print(f"ERROR : {e}")
                pass
        return False

    def close_browser(self):
        if self.driver:
            self.driver.quit()
    
    def download_file(self, download_url, target_folder):
        headers = {
            "Cookie": self.cookies,
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
            file_path = f"{target_folder}/{file_name}"
            with open(file_path, "wb") as file:
                file.write(response.content)
            full_path = os.path.join(os.getcwd(), file_path)
            return full_path

    def get_payment_files(self, name: str):
        self.driver.get("https://ciclade.caissedesdepots.fr/monespace/#/service/mes-demandes")
        self.driver.refresh()
        self.enter_text_in_element('//div[@id="mes-demandes_filter"]//input', f"{name}", show_error=False)
        download_urls = []
        if self.wait_for_element('//table[@id="mes-demandes"]/tbody/tr/td[6]'):
            status = self.driver.find_element(By.XPATH, '//table[@id="mes-demandes"]/tbody/tr/td[5]').get_attribute("innerText")
            print(f"--------->  {status}")
            if(status == "Paiement effectué"):
                self.click_element('//table[@id="mes-demandes"]/tbody/tr/td[6]/span/a')
                if self.wait_for_element('//i[@class="fa fa-download"]/parent::a'):
                    elements = self.driver.find_elements(By.XPATH, '//i[@class="fa fa-download"]/parent::a')
                    for element in elements:
                        download_url = element.get_attribute("href")
                        download_urls.append(download_url)
                time.sleep(1)
                return (1, download_urls)
            if(status == "Rejetée"):
                return (-1, download_urls)
        return (0, download_urls)