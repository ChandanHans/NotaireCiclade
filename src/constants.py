import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))

GPT_KEY = os.environ["GPT_KEY"]
CREDS_JSON = json.loads(os.environ["CREDS_JSON"])
SAVE_FILE = "settings.pkl"
SETTING_KEY = b"aY7EMKzTHYyo_gkcVoIBTUTAsWSTt2SJsbbMBwxzWsQ="
NOTARY_SHEET_ID = "1C-5OCv2Nvkr8ZSrfpnO1D5K8-kzybsu5bUa6eQL6Bj0"
FACTURES_SHEET_ID = "1nuWrAZB4XF2Jlo_IaLPxRra-13H_fQffbTT1LBJyqVM"
