import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def generate(prompt: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a CBSE question paper generator."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content