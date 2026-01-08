#!/usr/bin/env python3
"""List available Gemini models"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found")
    exit(1)

client = genai.Client(api_key=api_key)

print("Available Gemini models:")
print("=" * 60)

try:
    models = client.models.list()
    for model in models:
        print(f"  • {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"    Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
