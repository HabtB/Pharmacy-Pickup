#!/usr/bin/env python3
"""
Simple test script to verify Groq API connectivity
"""

import os
import requests
import json
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    
    if env_path.exists():
        print(f"📁 Loading .env from: {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ .env file loaded")
    else:
        print(f"❌ .env file not found at: {env_path}")

def test_groq_api():
    """Test if Groq API is working"""
    
    # Load .env file first
    load_env_file()
    
    # Get API key from environment
    api_key = os.getenv('GROK_API_KEY')
    if not api_key:
        print("❌ GROK_API_KEY not found in environment")
        print("💡 Check your .env file has: GROK_API_KEY=your_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test API endpoint
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hello, just testing the API. Please respond with 'API working'."
            }
        ],
        "model": "llama-3.1-70b-versatile",
        "stream": False,
        "temperature": 0.1
    }
    
    try:
        print("🔄 Testing Groq API...")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ API Response: {content}")
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"❌ Error Details: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ API Timeout (>10 seconds)")
        return False
    except Exception as e:
        print(f"❌ API Exception: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Groq API Connection...")
    success = test_groq_api()
    
    if success:
        print("\n🎉 Groq API is working!")
    else:
        print("\n💥 Groq API test failed!")
