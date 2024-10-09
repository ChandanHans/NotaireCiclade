import requests
from collections import Counter

from .utils import *



def get_max_repeated_value(my_list):
    counter = Counter(my_list)
    max_repeated = counter.most_common(1)[0][0]  # Get the most common element
    return max_repeated

def get_captcha_result(client, url):
    results = []
    print("----------------------")
    for _ in range(5):
        response = requests.get(url)
        with open("captcha.wav", "wb") as f:
            f.write(response.content)
        audio_file = open("captcha.wav", "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, language="fr"
        )
        gpt_response = transcription.text
        result = ''.join(char if char.isalnum() else '' for char in gpt_response)
        results.append(result)
    final_result = get_max_repeated_value(results)
    print(f"{results} = {final_result}")
    print("----------------------")
    return final_result
