#!/usr/bin/env python3
"""
Test script to validate the application flow and identify issues
"""

import os
import sys
import json
from pathlib import Path

# Test results
results = {
    "environment": {},
    "imports": {},
    "api_compatibility": {},
    "file_structure": {},
    "potential_issues": []
}

print("=" * 60)
print("GEORGIAN VOICEOVER APP - FLOW VALIDATION TEST")
print("=" * 60)

# 1. Check Environment Variables
print("\n1. CHECKING ENVIRONMENT VARIABLES...")
env_vars = [
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "FLASK_PORT",
    "MAX_VIDEO_LENGTH",
    "OUTPUT_DIR",
    "TEMP_DIR",
    "ORIGINAL_AUDIO_VOLUME",
    "VOICEOVER_VOLUME",
    "WHISPER_MODEL",
    "RAPIDAPI_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
    "R2_PUBLIC_URL",
    "DATABASE_URL",
    "REDIS_URL"
]

from dotenv import load_dotenv
load_dotenv()

for var in env_vars:
    value = os.getenv(var)
    if value:
        results["environment"][var] = "SET" if "KEY" in var or "SECRET" in var else value[:20] + "..."
        print(f"  ✓ {var}: {'***' if 'KEY' in var or 'SECRET' in var else 'SET'}")
    else:
        results["environment"][var] = "NOT SET"
        print(f"  ✗ {var}: NOT SET")

# 2. Check Required Imports
print("\n2. CHECKING REQUIRED PACKAGES...")
packages = {
    "flask": "Flask",
    "flask_cors": "flask-cors",
    "celery": "Celery",
    "redis": "Redis",
    "openai": "OpenAI",
    "elevenlabs": "ElevenLabs",
    "httpx": "httpx",
    "ffmpeg": "ffmpeg-python",
    "sqlalchemy": "SQLAlchemy",
    "psycopg2": "psycopg2-binary",
    "boto3": "boto3",
    "gunicorn": "Gunicorn",
    "structlog": "structlog",
    "pythonjsonlogger": "python-json-logger",
    "dotenv": "python-dotenv",
    "tqdm": "tqdm",
    "requests": "requests"
}

for module, name in packages.items():
    try:
        __import__(module)
        results["imports"][name] = "OK"
        print(f"  ✓ {name}: INSTALLED")

        # Check version for critical packages
        if module == "openai":
            import openai
            version = openai.__version__ if hasattr(openai, '__version__') else "unknown"
            print(f"    → OpenAI version: {version}")
            if version.startswith("0."):
                results["api_compatibility"]["openai"] = "COMPATIBLE (v0.x API)"
            else:
                results["api_compatibility"]["openai"] = "INCOMPATIBLE (v1.x API - code uses v0.x syntax)"
                results["potential_issues"].append("OpenAI library version mismatch - code expects v0.28.1")

    except ImportError:
        results["imports"][name] = "MISSING"
        print(f"  ✗ {name}: NOT INSTALLED")

# 3. Check File Structure
print("\n3. CHECKING FILE STRUCTURE...")
required_dirs = ["src", "templates", "static", "output", "temp"]
required_files = [
    "app.py",
    "celery_app.py",
    "requirements.txt",
    "src/tasks.py",
    "src/database.py",
    "src/downloader.py",
    "src/transcriber.py",
    "src/translator.py",
    "src/tts.py",
    "src/audio_mixer.py",
    "src/storage.py",
    "src/validators.py",
    "src/video_processor.py",
    "src/logging_config.py"
]

for dir_name in required_dirs:
    if os.path.isdir(dir_name):
        results["file_structure"][dir_name] = "EXISTS"
        print(f"  ✓ Directory: {dir_name}")
    else:
        results["file_structure"][dir_name] = "MISSING"
        print(f"  ✗ Directory: {dir_name} - MISSING")

for file_name in required_files:
    if os.path.isfile(file_name):
        size = os.path.getsize(file_name)
        results["file_structure"][file_name] = f"EXISTS ({size} bytes)"
        print(f"  ✓ File: {file_name} ({size} bytes)")
    else:
        results["file_structure"][file_name] = "MISSING"
        print(f"  ✗ File: {file_name} - MISSING")

# 4. Check External Tools
print("\n4. CHECKING EXTERNAL TOOLS...")
import subprocess

# Check ffmpeg
try:
    result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
    if result.returncode == 0:
        ffmpeg_path = result.stdout.strip()
        version_result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "unknown"
        print(f"  ✓ ffmpeg: {ffmpeg_path}")
        print(f"    → Version: {version}")
        results["file_structure"]["ffmpeg"] = f"FOUND at {ffmpeg_path}"
    else:
        print(f"  ✗ ffmpeg: NOT FOUND")
        results["file_structure"]["ffmpeg"] = "NOT FOUND"
        results["potential_issues"].append("ffmpeg not found - required for audio/video processing")
except Exception as e:
    print(f"  ✗ ffmpeg: ERROR - {e}")
    results["file_structure"]["ffmpeg"] = f"ERROR: {e}"

# Check Redis
try:
    result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
    if result.returncode == 0 and 'PONG' in result.stdout:
        print(f"  ✓ Redis: RUNNING")
        results["file_structure"]["redis"] = "RUNNING"
    else:
        print(f"  ✗ Redis: NOT RUNNING (app will use threading mode)")
        results["file_structure"]["redis"] = "NOT RUNNING"
        results["potential_issues"].append("Redis not running - Celery unavailable, using threading fallback")
except FileNotFoundError:
    print(f"  ✗ Redis: NOT INSTALLED")
    results["file_structure"]["redis"] = "NOT INSTALLED"
    results["potential_issues"].append("Redis not installed - Celery unavailable, using threading fallback")

# 5. Analyze Critical Issues
print("\n5. CRITICAL ISSUES IDENTIFIED:")
if not results["potential_issues"]:
    print("  ✓ No critical issues found")
else:
    for issue in results["potential_issues"]:
        print(f"  ⚠️  {issue}")

# Additional checks based on audit findings
print("\n6. CODE QUALITY ISSUES FROM AUDIT:")
code_issues = [
    "Dead code: Google Cloud Speech-to-Text method (~50 lines) never called",
    "Unused imports in app.py: sys, traceback, uuid, urlparse, parse_qs, AsyncResult",
    "Memory leak risk: Unclosed HTTP sessions in downloader.py",
    "Resource leak: Database sessions not properly closed in some paths",
    "4 different implementations of video ID extraction (should be consolidated)",
    "Bare except clauses in storage.py swallow errors silently",
    "Race condition: processing_status dict accessed without locks in threading mode",
    "Missing timeouts on external API calls could hang forever",
    "~200 lines of dead code total (8% of codebase)",
    "Duplicate progress update functions in app.py and tasks.py"
]

for issue in code_issues:
    print(f"  • {issue}")

# 7. Performance and Security Concerns
print("\n7. PERFORMANCE & SECURITY CONCERNS:")
concerns = [
    "No resource limits on video file size (only duration check)",
    "No memory usage limits during ffmpeg operations",
    "Temp files only cleaned on success, not on crashes",
    "Complex ffmpeg filter chains built in memory for large videos",
    "No rate limiting for API calls",
    "Path traversal risk in download route (mitigated but fragile)",
    "Environment variables cast without validation (could crash on bad values)"
]

for concern in concerns:
    print(f"  • {concern}")

# 8. Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

# Count issues
missing_packages = sum(1 for v in results["imports"].values() if v == "MISSING")
missing_env_vars = sum(1 for v in results["environment"].values() if v == "NOT SET")
missing_files = sum(1 for k, v in results["file_structure"].items() if v == "MISSING")

print(f"\nEnvironment Variables: {len(env_vars) - missing_env_vars}/{len(env_vars)} set")
print(f"Required Packages: {len(packages) - missing_packages}/{len(packages)} installed")
print(f"Required Files/Dirs: {len(required_dirs) + len(required_files) - missing_files}/{len(required_dirs) + len(required_files)} present")
print(f"Critical Issues: {len(results['potential_issues'])}")
print(f"Code Quality Issues: {len(code_issues)}")
print(f"Performance/Security Concerns: {len(concerns)}")

# Overall status
can_run = missing_packages == 0 and missing_files == 0
api_compatible = results.get("api_compatibility", {}).get("openai") != "INCOMPATIBLE (v1.x API - code uses v0.x syntax)"

print("\n" + "=" * 60)
if can_run and api_compatible:
    print("✅ APPLICATION CAN RUN (but may have issues)")
elif not can_run:
    print("❌ APPLICATION CANNOT RUN - Missing dependencies")
else:
    print("⚠️  APPLICATION WILL FAIL - API version mismatch")
print("=" * 60)

# Save results to file
with open('flow_test_results.json', 'w') as f:
    json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: flow_test_results.json")