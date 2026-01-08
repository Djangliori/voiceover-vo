"""
Test Whisper Model Download
ეს script გიჩვენებთ როგორ ჩამოიტვირთება Whisper model
"""

import whisper
import os

print("=" * 60)
print("  Whisper Model Download Test")
print("=" * 60)
print()

# Check cache folder
cache_dir = os.path.expanduser("~/.cache/whisper")
print(f"Cache folder: {cache_dir}")

if os.path.exists(cache_dir):
    files = os.listdir(cache_dir)
    if files:
        print(f"[OK] Model already downloaded: {files}")
    else:
        print("[EMPTY] Cache folder is empty")
else:
    print("[NOT FOUND] Cache folder does not exist - model not downloaded yet")

print()
print("-" * 60)
print("Starting 'base' model download...")
print("Please wait 1-2 minutes - first time will download ~140MB")
print("-" * 60)
print()

try:
    # Load model (will download if not cached)
    model = whisper.load_model("base")
    print()
    print("=" * 60)
    print("SUCCESS! Whisper model downloaded and ready!")
    print("=" * 60)
    print()

    # Show cache files
    if os.path.exists(cache_dir):
        files = os.listdir(cache_dir)
        print(f"Cache files: {files}")
        for file in files:
            size = os.path.getsize(os.path.join(cache_dir, file)) / (1024*1024)
            print(f"  - {file}: {size:.1f} MB")

    print()
    print("You can now use the app - model is ready!")

except Exception as e:
    print(f"[ERROR] {e}")
