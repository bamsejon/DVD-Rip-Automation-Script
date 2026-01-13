#!/usr/bin/env python3

import os
import subprocess
import sys
import json
import urllib.parse
import urllib.request
import re
from dotenv import load_dotenv

# ========= ENV =========

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if not OMDB_API_KEY:
    print("❌ OMDB_API_KEY not set (check .env)")
    sys.exit(1)

# ========= CONFIG =========

MAKE_MKV_PATH = "/Applications/MakeMKV.app/Contents/MacOS/makemkvcon"
HANDBRAKE_CLI_PATH = "/opt/homebrew/bin/HandBrakeCLI"

TEMP_DIR = "/Volumes/Jonte/rip/tmp"
MOVIES_DIR = "/Volumes/nfs-share/media/rippat/movies"

# DVD-optimalt
HANDBRAKE_PRESET = "HQ 720p30 Surround"

# ========= HELPERS =========

def run_command(cmd, capture_output=False):
    print("\n>>>", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT
    )

# ========= DVD DETECTION =========

def get_dvd_volume_label():
    """
    Detect DVD by VIDEO_TS folder – 100% reliable.
    """
    for name in os.listdir("/Volumes"):
        path = os.path.join("/Volumes", name)
        if not os.path.ismount(path):
            continue

        if (
            os.path.isdir(os.path.join(path, "VIDEO_TS")) or
            os.path.isdir(os.path.join(path, "video_ts"))
        ):
            return name

    return None

def normalize_title(volume_label):
    """
    Sanitize ugly DVD volume names like:
    <PADDINGTON>, [ALIEN], MOVIE_DISC_1
    """
    title = volume_label

    # Remove common junk characters
    title = re.sub(r"[<>[\]()]", "", title)

    # Replace separators with space
    title = title.replace("_", " ").replace(".", " ")

    # Collapse whitespace
    title = re.sub(r"\s+", " ", title)

    return title.strip()

# ========= OMDB =========

def omdb_lookup(title):
    print(f"\n🔎 OMDb lookup: {title}")

    query = urllib.parse.quote(title)
    url = f"https://www.omdbapi.com/?t={query}&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        print(f"❌ OMDb lookup failed for '{title}'")
        sys.exit(1)

    return {
        "title": data["Title"],
        "year": data["Year"]
    }

# ========= MAKEMKV =========

def rip_with_makemkv(title_id=0):
    print("\n🎬 Ripping disc...")

    # Clean temp dir
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            p = os.path.join(TEMP_DIR, f)
            if os.path.isfile(p):
                os.remove(p)
    else:
        os.makedirs(TEMP_DIR, exist_ok=True)

    cmd = [
        MAKE_MKV_PATH,
        "mkv",
        "disc:0",
        str(title_id),
        TEMP_DIR
    ]

    run_command(cmd)

    mkvs = [f for f in os.listdir(TEMP_DIR) if f.lower().endswith(".mkv")]
    if not mkvs:
        print("❌ No MKV produced by MakeMKV")
        sys.exit(1)

    if len(mkvs) > 1:
        print("⚠️ Multiple MKVs found, using first one")

    return os.path.join(TEMP_DIR, mkvs[0])

# ========= HANDBRAKE =========

def compress_with_handbrake(input_file, output_file):
    print(f"\n🎞 Compressing: {input_file}")

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

    # 1️⃣ Detect DVD
    dvd_label = get_dvd_volume_label()
    if not dvd_label:
        print("❌ Could not detect DVD (VIDEO_TS missing)")
        sys.exit(1)

    query_title = normalize_title(dvd_label)
    print(f"🎞 Detected DVD title: {query_title}")

    # 2️⃣ OMDb
    movie = omdb_lookup(query_title)
    title = movie["title"]
    year = movie["year"]

    print(f"✅ Identified: {title} ({year})")

    # 3️⃣ Jellyfin structure
    movie_folder = f"{title} ({year})"
    movie_path = os.path.join(MOVIES_DIR, movie_folder)
    os.makedirs(movie_path, exist_ok=True)

    output_file = os.path.join(movie_path, f"{title} ({year}).mkv")

    # 4️⃣ Rip
    ripped_mkv = rip_with_makemkv()

    # 5️⃣ Transcode
    compress_with_handbrake(ripped_mkv, output_file)

    # 6️⃣ Cleanup
    if os.path.exists(ripped_mkv):
        print(f"🧹 Removing raw MKV: {ripped_mkv}")
        os.remove(ripped_mkv)

    print("\n🎉 DONE")
    print(f"📁 Jellyfin-ready at: {movie_path}")

# ========= ENTRY =========

if __name__ == "__main__":
    main()