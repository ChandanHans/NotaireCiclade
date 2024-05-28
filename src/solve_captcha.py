import requests
from openai import OpenAI

from .constants import GPT_KEY
from .utils import *

client = OpenAI(api_key=GPT_KEY)


def get_captcha_result(url):
    response = requests.get(url)
    with open("captcha.wav", "wb") as f:
        f.write(response.content)
    audio_file = open("captcha.wav", "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file, language="fr"
    )
    gpt_response = transcription.text
    result = ''.join(char if char.isalnum() else '' for char in gpt_response)
    
    return result
