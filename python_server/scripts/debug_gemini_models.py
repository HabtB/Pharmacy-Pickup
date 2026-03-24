
import os
import google.generativeai as genai
from dotenv import load_dotenv


# Explicitly load from local directory first
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

api_key = os.getenv('GOOGLE_API_KEY')
print(f"DEBUG: Loaded API Key from: {env_path.absolute()}")
if api_key:
    print(f"DEBUG: Key loaded: {api_key[:10]}...{api_key[-5:] if len(api_key)>5 else ''}")
else:
    print("DEBUG: No GOOGLE_API_KEY found!")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment")
    exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} (Display: {m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")
