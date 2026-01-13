#!/usr/bin/env python3

import os
import subprocess
import sys
import json
import urllib.request

# ========= CONFIG =========

MAKE_MKV_PATH = "/Applications/MakeMKV.app/Contents/MacOS/makemkvcon"
HANDBRAKE_CLI_PATH = "/opt/homebrew/bin/HandBrakeCLI"

OMDB_API_KEY = os.getenv("OMDB_API_KEY")

if not OMDB_API_KEY:
    print("❌ OMDB_API_KEY not set")
    sys.exit(1)

# Base directories
TEMP_DIR = "/Volumes/nfs-share/media/rippat/tmp"
MOVIES_DIR = "/Volumes/nfs-share/media/movies"

HANDBRAKE_PRESET = "HQ 1080p30 Surround"

# ========= HELPERS =========

def run_command(cmd):
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, check=True)

def omdb_lookup(title):
    print(f"\n🔎 Looking up OMDb: {title}")
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        print("❌ OMDb lookup failed")
        sys.exit(1)

    return data["Title"], data["Year"]

# ========= MAKEMKV =========

def rip_with_makemkv(title_id=0):
    os.makedirs(TEMP_DIR, exist_ok=True)

    cmd = [
        MAKE_MKV_PATH,
        "mkv",
        "disc:0",
        str(title_id),
        TEMP_DIR
    ]

    run_command(cmd)

    mkvs = [f for f in os.listdir(TEMP_DIR) if f.endswith(".mkv")]
    if not mkvs:
        print("❌ No MKV produced by MakeMKV")
        sys.exit(1)

    return os.path.join(TEMP_DIR, mkvs[0])

# ========= HANDBRAKE =========

def compress_with_handbrake(input_file, output_file):
    cmd = [
        HANDBRAKE_CLI_PATH,
        "-i", input_file,
        "-o", output_file,
        "--preset", HANDBRAKE_PRESET,
        "--all-subtitles",
        "--subtitle-burned=0",
        "--format", "mkv"
    ]

    run_command(cmd)

# ========= MAIN =========

def main():
    os.makedirs(MOVIES_DIR, exist_ok=True)

    # 1️⃣ Ask for movie title (first version = explicit)
    movie_query = input("🎬 Movie title (e.g. Alien Resurrection): ").strip()

    # 2️⃣ OMDb lookup
    title, year = omdb_lookup(movie_query)
    print(f"✅ Identified: {title} ({year})")

    # 3️⃣ Create Jellyfin folder
    movie_folder = f"{title} ({year})"
    movie_path = os.path.join(MOVIES_DIR, movie_folder)
    os.makedirs(movie_path, exist_ok=True)

    output_file = os.path.join(
        movie_path,
        f"{title} ({year}).mkv"
    )

    # 4️⃣ Rip
    ripped_mkv = rip_with_makemkv()

    # 5️⃣ Compress
    compress_with_handbrake(ripped_mkv, output_file)

    print("\n🎉 DONE")
    print(f"📁 Jellyfin-ready at: {movie_path}")

# ========= ENTRY =========

if __name__ == "__main__":
    main()