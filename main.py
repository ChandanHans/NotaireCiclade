from src.automation_process import AutomationProcess
from src.utils import *
from src.constants import *
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
                print("Password correct. Decryption successful!")
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
                break
        os.system("cls")
        print("Enter your Ciclade informations:-\n\n")
        user_data = get_user_input()
        encrypt_user_data(user_data, derived_key)
    print("\n\n\n")

    automation = AutomationProcess(user_data)  # Create an instance of AutomationProcess with user_data
    automation.start_process()  # Start the automation process


if __name__ == "__main__":
    if not os.path.exists(RECAP_FOLDER):
        os.makedirs(RECAP_FOLDER)
    if not os.path.exists(DOCUMENT_FOLDER):
        os.makedirs(DOCUMENT_FOLDER)
        
    try:
        main()
    except Exception as e:
        print(e)
    input("Press Enter To Exit:")
