from src.ciclade_api_session import CicladeApiSession
from src.submit_cases import SubmitCases
from src.utils import *
from src.constants import *
from src.upload_files import UploadFiles
from prompt_toolkit import prompt


def main():
    while True:
        os.system("cls")
        env_file_path = ENV_FILE

        with open(env_file_path, 'rb') as file:
            salt = file.read(16)

        derived_key = load_derived_key()

        # Step 1: Prompt for Klero password and derive the key if not already saved
        while not derived_key:
            password = prompt("Enter Klero password: ", is_password=True)
            derived_key = derive_key(password, salt)
            decrypted_data = load_env_from_encrypted_file(derived_key, env_file_path)

            if decrypted_data:
                print("Correct Password.")
                save_derived_key(derived_key)
            else:
                print("Incorrect password. Please try again.")
                derived_key = None
        load_env_from_encrypted_file(derived_key, env_file_path)
        # Load or ask for new user data
        user_data = load_saved_data(derived_key)
        if user_data:
            print("\n---------------  User Data  ---------------\n\n")
            for key, value in user_data.items():
                if key == "Password":
                    print(f"{key}: {'*' * len(value)}")  # Display password as asterisks for security
                else:
                    print(f"{key}: {value}")

            # Ask if the user wants to continue with the old data or change it
            choice = input("\nDo you want to continue with this data? (y/n): ").strip().lower()
            if choice != 'n':
                encrypt_user_data(user_data, derived_key)
                break
            
        print("Enter your Ciclade informations:-\n\n")
        if not user_data:
            user_data = get_user_input()
        else:
            user_data = ask_for_new_data(user_data)
        encrypt_user_data(user_data, derived_key)
    print("\n\n\n")
    
    session = CicladeApiSession(user_data)
    if session and session.user_info:
        while True:
            print("\nSelect an option:")
            print("1. Submit All Cases")
            print("2. Upload Payment Files")
            print("3. Exit")
            option = input("\nEnter your choice: ").strip()
            if option in ["1","2","3"]:
                break
            else:
                print("Invalid choice! Please select a valid option.")
                
        if option == "1":
            automation = SubmitCases(session)  # Create an instance of SubmitCases with user_data
            automation.start_process()  # Start the automation process
        elif option == "2":
            automation = UploadFiles(session)  # Create an instance of SubmitCases with user_data
            automation.start_process()  # Start the automation process
        elif option == "3":
            exit()
    else:
        print("Try Again Later!!")


if __name__ == "__main__":
    if not os.path.exists(RECAP_FOLDER):
        os.makedirs(RECAP_FOLDER)
    if not os.path.exists(PAYMENT_FOLDER):
        os.makedirs(PAYMENT_FOLDER)
    if not os.path.exists(DOCUMENT_FOLDER):
        os.makedirs(DOCUMENT_FOLDER)
        
    while True:
        try:
            main()
            input("Press Enter To Continue:")
        except Exception as e:
            print(f"An error occurred: {e}")
            input("Press Enter To Exit:")
            break
