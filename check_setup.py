#!/usr/bin/env python3
"""
Setup Verification Script
შეამოწმებს ffmpeg და API keys კონფიგურაციას
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()

print("=" * 70)
print("  🔍 Georgian Voiceover App - Setup Verification")
print("=" * 70)
print()

# Track issues
issues = []
warnings = []
success = []

# 1. Check ffmpeg
print("1️⃣  Checking ffmpeg...")
try:
    result = subprocess.run(['ffmpeg', '-version'],
                          capture_output=True,
                          text=True,
                          timeout=5)
    if result.returncode == 0:
        version = result.stdout.split('\n')[0]
        print(f"   ✅ ffmpeg installed: {version}")
        success.append("ffmpeg")
    else:
        print("   ❌ ffmpeg not working properly")
        issues.append("ffmpeg installation issue")
except FileNotFoundError:
    print("   ❌ ffmpeg not found in PATH")
    issues.append("ffmpeg not installed")
except Exception as e:
    print(f"   ❌ ffmpeg check failed: {e}")
    issues.append("ffmpeg error")

print()

# 2. Check Voicegain API Key
print("2️⃣  Checking Voicegain API Key...")
voicegain_key = os.getenv('VOICEGAIN_API_KEY')
if voicegain_key and voicegain_key != 'your_voicegain_jwt_token_here':
    if voicegain_key.startswith('eyJ'):
        print(f"   ✅ Voicegain API key configured (JWT token, {len(voicegain_key)} chars)")
        success.append("Voicegain API")
    else:
        print("   ⚠️  Voicegain key doesn't look like a JWT token")
        warnings.append("Voicegain key format")
else:
    print("   ❌ Voicegain API key not configured")
    issues.append("Voicegain API key")

print()

# 3. Check OpenAI API Key
print("3️⃣  Checking OpenAI API Key...")
openai_key = os.getenv('OPENAI_API_KEY')
if openai_key and openai_key != 'your_openai_api_key_here':
    if openai_key.startswith('sk-'):
        print(f"   ✅ OpenAI API key configured ({openai_key[:15]}...)")
        success.append("OpenAI API")
    else:
        print("   ⚠️  OpenAI key doesn't start with 'sk-'")
        warnings.append("OpenAI key format")
else:
    print("   ❌ OpenAI API key not configured")
    issues.append("OpenAI API key")

print()

# 4. Check Google Cloud Credentials
print("4️⃣  Checking Google Cloud Credentials...")
google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
google_creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

if google_creds_json:
    print(f"   ✅ Google credentials (JSON inline, {len(google_creds_json)} chars)")
    success.append("Google Cloud TTS")
elif google_creds_path and google_creds_path != '/path/to/google-credentials.json':
    # Normalize path
    creds_path = Path(google_creds_path)
    if creds_path.exists():
        print(f"   ✅ Google credentials file found: {creds_path}")
        # Check if it's valid JSON
        try:
            import json
            with open(creds_path, 'r') as f:
                data = json.load(f)
                if 'type' in data and data['type'] == 'service_account':
                    print(f"   ✅ Valid service account credentials")
                    success.append("Google Cloud TTS")
                else:
                    print(f"   ⚠️  Credentials file doesn't look like a service account")
                    warnings.append("Google credentials format")
        except json.JSONDecodeError:
            print(f"   ❌ Credentials file is not valid JSON")
            issues.append("Google credentials invalid JSON")
        except Exception as e:
            print(f"   ⚠️  Could not validate credentials: {e}")
            warnings.append("Google credentials validation")
    else:
        print(f"   ❌ Google credentials file not found: {creds_path}")
        issues.append("Google credentials file missing")
else:
    print("   ❌ Google Cloud credentials not configured")
    issues.append("Google Cloud credentials")

print()

# 5. Check RapidAPI (Optional)
print("5️⃣  Checking RapidAPI Key (Optional)...")
rapidapi_key = os.getenv('RAPIDAPI_KEY')
if rapidapi_key and rapidapi_key != 'your_rapidapi_key_here':
    print(f"   ✅ RapidAPI key configured")
    success.append("RapidAPI (optional)")
else:
    print("   ⚠️  RapidAPI key not configured (will use yt-dlp fallback)")
    warnings.append("RapidAPI not configured (optional)")

print()

# 6. Check .env file
print("6️⃣  Checking .env file...")
env_path = Path('.env')
if env_path.exists():
    print(f"   ✅ .env file exists")
    success.append(".env file")
else:
    print(f"   ❌ .env file not found")
    issues.append(".env file missing")

print()

# Summary
print("=" * 70)
print("  📊 Summary")
print("=" * 70)
print()

if success:
    print("✅ Configured successfully:")
    for item in success:
        print(f"   • {item}")
    print()

if warnings:
    print("⚠️  Warnings:")
    for item in warnings:
        print(f"   • {item}")
    print()

if issues:
    print("❌ Issues found:")
    for item in issues:
        print(f"   • {item}")
    print()
    print("🔧 Please fix these issues before running the app.")
    print()
    print("📖 See these guides:")
    print("   • API Keys: API_SETUP_STEP_BY_STEP.md")
    print("   • ffmpeg: INSTALL_FFMPEG_WINDOWS.md")
    sys.exit(1)
else:
    print("🎉 All required components are configured!")
    print()
    print("🚀 You can now start the application:")
    print("   PYTHONIOENCODING=utf-8 python app.py")
    print()
    print("🌐 Then open: http://localhost:5001")
    print()
    print("🔐 Login with:")
    print("   Email:    admin@test.com")
    print("   Password: testpassword123")
    sys.exit(0)
