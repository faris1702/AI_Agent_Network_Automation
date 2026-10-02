from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# It will automatically look for an environment variable named OPENAI_API_KEY,
# or you can pass it manually: client = OpenAI(api_key="YOUR_API_KEY")
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "I am testing if the API key works"}]
    )
    print("Success! Response:", response.choices[0].message.content)
except Exception as e:
    print("API Key Test Failed:", e)
