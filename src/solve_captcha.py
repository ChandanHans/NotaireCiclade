import requests
from collections import Counter
from openai import OpenAI

from .utils import *

gpt_client = OpenAI(api_key=os.environ["GPT_KEY"])

def get_max_repeated_value(my_list):
    counter = Counter(my_list)
    max_repeated = counter.most_common(1)[0][0]  # Get the most common element
    return max_repeated

def get_captcha_result(base64url):
    response = gpt_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "give me the text of this image in json {'text': ''}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": base64url},
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    result : dict = eval(response.choices[0].message.content)
    result_text : str = result.get("text")
    final_text = ''.join(char if char.isalnum() else '' for char in result_text)
    print(f"Captcha : {final_text}")
    return final_text
