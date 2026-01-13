#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import urllib.parse
import urllib.request
from dotenv import load_dotenv

# =========================================================
# ENV
# =========================================================

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
if not OMDB_API_KEY:
    print("❌ OMDB_API_KEY not set (check .env)")
    sys.exit(1)

# =========================================================
# PATHS / CONFIG
# =========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_PATH = os.path.join(SCRIPT_DIR, "title_overrides.json")

MAKE_MKV_PATH = "/Applications/MakeMKV.app/Contents/MacOS/makemkvcon"
HANDBRAKE_CLI_PATH = "/opt/homebrew/bin/HandBrakeCLI"

TEMP_DIR = "/Volumes/Jonte/rip/tmp"
MOVIES_DIR = "/Volumes/nfs-share/media/rippat/movies"

# DVD preset (Blu-ray kan senare få egen)
HANDBRAKE_PRESET = "HQ 720p30 Surround"

# =========================================================
# HELPERS
# =========================================================

def run_command(cmd, capture_output=False):
    print("\n>>>", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.STDOUT
    )

# =========================================================
# LOAD OVERRIDES
# =========================================================

def load_overrides():
    if not os.path.exists(OVERRIDES_PATH):
        return {}

    with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

TITLE_OVERRIDES = load_overrides()

# =========================================================
# DISC DETECTION
# =========================================================

def detect_disc_volume():
    for name in os.listdir("/Volumes"):
        path = os.path.join("/Volumes", name)
        if not os.path.ismount(path):
            continue

        upper = name.upper()

        if upper.startswith(("BACKUP", "TIME MACHINE")):
            continue

        if any(x in upper for x in ["DVD", "DISC", "BD", "BLURAY", "_"]):
            return name

    return None

def normalize_volume_label(label):
    title = label.replace("_", " ").replace(".", " ").strip()
    title = title.replace("  ", " ")

    for token in ["DISC 1", "DISC 2", "DISC 3", "D1", "D2"]:
        title = title.replace(token, "")

    return title.title().strip()

def detect_disc_type(volume_label):
    upper = volume_label.upper()
    if "BD" in upper or "BLURAY" in upper:
        return "BLURAY"
    return "DVD"

# =========================================================
# OMDB
# =========================================================

def omdb_lookup_by_imdb_id(imdb_id):
    print(f"\n🎯 OMDb lookup by IMDb ID: {imdb_id}")
    url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        print(f"❌ OMDb lookup failed for IMDb ID {imdb_id}")
        sys.exit(1)

    return data

def omdb_fuzzy_lookup(title):
    print(f"\n🔎 OMDb fuzzy lookup: {title}")
    query = urllib.parse.quote(title)
    url = f"https://www.omdbapi.com/?s={query}&type=movie&apikey={OMDB_API_KEY}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    if data.get("Response") != "True":
        print(f"❌ OMDb search failed for '{title}'")
        sys.exit(1)

    imdb_id = data["Search"][0]["imdbID"]
    return omdb_lookup_by_imdb_id(imdb_id)

# =========================================================
# MAKEMKV
# =========================================================

def rip_with_makemkv(title_id=0):
    print("\n🎬 Ripping disc with MakeMKV...")

    os.makedirs(TEMP_DIR, exist_ok=True)

    # Clean temp dir
    for f in os.listdir(TEMP_DIR):
        p = os.path.join(TEMP_DIR, f)
        if os.path.isfile(p):
            os.remove(p)

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

    return os.path.join(TEMP_DIR, mkvs[0])

# =========================================================
# HANDBRAKE
# =========================================================

def compress_with_handbrake(input_file, output_file):
    print(f"\n🎞 Transcoding with HandBrake: {input_file}")

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

# =========================================================
# EJECT
# =========================================================

def eject_disc(volume_label):
    print(f"\n⏏️ Ejecting disc: {volume_label}")
    subprocess.run(["diskutil", "eject", f"/Volumes/{volume_label}"], check=False)

# =========================================================
# MAIN
# =========================================================

def main():
    os.makedirs(MOVIES_DIR, exist_ok=True)

    volume = detect_disc_volume()
    if not volume:
        print("❌ Could not detect disc volume")
        sys.exit(1)

    print(f"🎞 Detected disc volume: {volume}")

    disc_type = detect_disc_type(volume)
    print(f"💿 Disc type: {disc_type}")

    normalized = normalize_volume_label(volume)
    print(f"🎬 Normalized title: {normalized}")

    # -----------------------------------------------------
    # METADATA RESOLUTION
    # -----------------------------------------------------

    if volume in TITLE_OVERRIDES:
        imdb_id = TITLE_OVERRIDES[volume]["imdb_id"]
        movie = omdb_lookup_by_imdb_id(imdb_id)
    else:
        movie = omdb_fuzzy_lookup(normalized)

    title = movie["Title"]
    year = movie["Year"]

    print(f"✅ Identified: {title} ({year})")

    # -----------------------------------------------------
    # JELLYFIN STRUCTURE
    # -----------------------------------------------------

    movie_folder = f"{title} ({year})"
    movie_path = os.path.join(MOVIES_DIR, movie_folder)
    os.makedirs(movie_path, exist_ok=True)

    output_file = os.path.join(movie_path, f"{title} ({year}).mkv")

    # -----------------------------------------------------
    # RIP + TRANSCODE
    # -----------------------------------------------------

    ripped_mkv = rip_with_makemkv()
    compress_with_handbrake(ripped_mkv, output_file)

    # Cleanup
    if os.path.exists(ripped_mkv):
        os.remove(ripped_mkv)

    eject_disc(volume)

    print("\n🎉 DONE")
    print(f"📁 Jellyfin-ready at: {movie_path}")

# =========================================================

if __name__ == "__main__":
    main()