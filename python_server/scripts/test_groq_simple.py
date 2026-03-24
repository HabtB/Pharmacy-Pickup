
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GROK_API_KEY')
print(f"Testing API Key: {api_key[:10]}..." if api_key else "NO KEY FOUND")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "messages": [
        {"role": "user", "content": "Return JSON: {\"status\": \"ok\"}"}
    ],
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.1, 
    "max_tokens": 10
}

try:
    print("Sending request...")
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
