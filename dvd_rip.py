#!/usr/bin/env python3

import os
import subprocess
import sys
import json
import urllib.parse
import urllib.request
import hashlib
import time
import requests
from dotenv import load_dotenv

# ==========================================================
# ENV
# ==========================================================

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
DISCFINDER_API = os.getenv("DISCFINDER_API", "https://discfinder-api.bylund.cloud")

if not OMDB_API_KEY:
    print("❌ OMDB_API_KEY not set (check .env)")
    sys.exit(1)

# ==========================================================
# CONFIG
# ==========================================================

MAKE_MKV_PATH = "/Applications/MakeMKV.app/Contents/MacOS/makemkvcon"
HANDBRAKE_CLI_PATH = "/opt/homebrew/bin/HandBrakeCLI"

TEMP_DIR = "/Volumes/Jonte/rip/tmp"
MOVIES_DIR = "/Volumes/nfs-share/media/rippat/movies"

HANDBRAKE_PRESET_DVD = "HQ 720p30 Surround"
HANDBRAKE_PRESET_BD  = "HQ 1080p30 Surround"

HANDBRAKE_AUDIO_PASSTHROUGH = [
    "--audio-copy-mask", "truehd,eac3,ac3,dts,dtshd",
    "--audio-fallback", "ac3"
]

# ==========================================================
# HELPERS
# ==========================================================

def run_command(cmd):
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, check=True)

def sha256_of_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# ==========================================================
# DISC DETECTION
# ==========================================================

def detect_disc():
    for name in os.listdir("/Volumes"):
        path = os.path.join("/Volumes", name)
        if not os.path.ismount(path):
            continue

        upper = name.upper()
        if upper.startswith(("BACKUP", "TIME MACHINE")):
            continue

        contents = os.listdir(path)

        if "BDMV" in contents:
            return name, "BLURAY"
        if "VIDEO_TS" in contents:
            return name, "DVD"

    return None, None

def normalize_title(volume_name):
    title = volume_name.replace("_", " ").replace("-", " ").title()
    for token in [" Disc 1", " Disc 2", " Disc 3", " Blu Ray", " Dvd"]:
        title = title.replace(token, "")
    return title.strip()

# ==========================================================
# OMDB
# ==========================================================

def omdb_lookup_by_title(title):
    query = urllib.parse.quote(title)
    url = f"https://www.omdbapi.com/?t={query}&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        return None

    return {
        "title": data["Title"],
        "year": data["Year"],
        "imdb_id": data["imdbID"],
    }

def omdb_lookup_by_imdb(imdb_id):
    url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        return None

    return {
        "title": data["Title"],
        "year": data["Year"],
        "imdb_id": data["imdbID"],
    }

# ==========================================================
# DISC FINDER API
# ==========================================================

def discfinder_lookup(disc_label, checksum):
    try:
        r = requests.get(
            f"{DISCFINDER_API}/lookup",
            params={"disc_label": disc_label, "checksum": checksum},
            timeout=5,
        )
        if r.status_code != 200:
            return None

        data = r.json()
        return {
            "title": data["title"],
            "year": data["year"],
            "imdb_id": data["imdb_id"],
        }
    except Exception:
        return None

def discfinder_post(payload):
    requests.post(
        f"{DISCFINDER_API}/discs",
        json=payload,
        timeout=5,
    )

# ==========================================================
# MAKEMKV
# ==========================================================

def rip_with_makemkv():
    print("\n🎬 Ripping disc...")

    os.makedirs(TEMP_DIR, exist_ok=True)

    for f in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, f)
        if os.path.isfile(path):
            os.remove(path)

    cmd = [
        MAKE_MKV_PATH,
        "mkv",
        "disc:0",
        "0",
        TEMP_DIR
    ]

    run_command(cmd)

    mkvs = [f for f in os.listdir(TEMP_DIR) if f.lower().endswith(".mkv")]
    if not mkvs:
        print("❌ No MKV produced by MakeMKV")
        sys.exit(1)

    return os.path.join(TEMP_DIR, mkvs[0])

# ==========================================================
# HANDBRAKE
# ==========================================================

def transcode(input_file, output_file, preset, disc_type):
    cmd = [
        HANDBRAKE_CLI_PATH,
        "-i", input_file,
        "-o", output_file,
        "--preset", preset,
        "--all-subtitles",
        "--subtitle-burned=0",
        "--subtitle-default=none",
        "--format", "mkv"
    ]

    if disc_type == "BLURAY":
        cmd.extend(HANDBRAKE_AUDIO_PASSTHROUGH)

    run_command(cmd)

# ==========================================================
# EJECT
# ==========================================================

def eject_disc(volume):
    time.sleep(10)
    subprocess.run(["diskutil", "eject", f"/Volumes/{volume}"], check=False)

# ==========================================================
# MAIN
# ==========================================================

def main():
    os.makedirs(MOVIES_DIR, exist_ok=True)

    volume, disc_type = detect_disc()
    if not volume:
        print("❌ No disc detected")
        sys.exit(1)

    print(f"\n🎞 Disc: {volume}")
    checksum = sha256_of_string(volume)
    print(f"🔐 Checksum: {checksum}")

    movie = discfinder_lookup(volume, checksum)

    if movie:
        print("✅ Found in Disc Finder API")
    else:
        normalized = normalize_title(volume)
        movie = omdb_lookup_by_title(normalized)

        if not movie:
            imdb_id = input("❌ OMDb failed. Enter IMDb ID or ENTER to abort: ").strip()
            if not imdb_id:
                sys.exit(1)

            movie = omdb_lookup_by_imdb(imdb_id)
            if not movie:
                print("❌ Invalid IMDb ID")
                sys.exit(1)

        print(f"\n🎬 Found via OMDb:")
        print(f"   Title: {movie['title']} ({movie['year']})")
        print(f"   IMDb:  https://www.imdb.com/title/{movie['imdb_id']}/")

        confirm = input("👉 Add this disc to Disc Finder API? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            discfinder_post({
                "disc_label": volume,
                "checksum": checksum,
                "disc_type": disc_type,
                "imdb_id": movie["imdb_id"],
                "title": movie["title"],
                "year": movie["year"],
            })
            print("💾 Added to Disc Finder API")

    print(f"\n▶️ Identified: {movie['title']} ({movie['year']})")

    movie_folder = f"{movie['title']} ({movie['year']})"
    movie_path = os.path.join(MOVIES_DIR, movie_folder)
    os.makedirs(movie_path, exist_ok=True)

    output_file = os.path.join(movie_path, f"{movie['title']} ({movie['year']}).mkv")

    raw = rip_with_makemkv()
    preset = HANDBRAKE_PRESET_BD if disc_type == "BLURAY" else HANDBRAKE_PRESET_DVD
    transcode(raw, output_file, preset, disc_type)

    os.remove(raw)
    eject_disc(volume)

    print("\n🎉 DONE")
    print(f"📁 Jellyfin-ready at: {movie_path}")

# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":
    main()