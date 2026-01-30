# includes/metadata_layout.py
import os
import time
import requests


def _get_api_url():
    """Get API URL lazily to ensure dotenv is loaded first"""
    return os.getenv("DISCFINDER_API", "https://disc-api.bylund.cloud")


def wait_for_metadata_layout_ready(checksum: str, poll_interval: int = 3):
    """
    Blocks until metadata_layout.status == 'ready'
    """
    print("\n⏳ Waiting for metadata layout to become READY...")
    print("   (admin selection in UI)")

    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0

    while True:
        r = requests.get(
            f"{_get_api_url()}/metadata-layout/{checksum}",
            timeout=5,
        )

        if r.status_code != 200:
            print("\n❌ Failed to fetch metadata layout status")
            print(r.text)
            raise SystemExit(1)

        status = r.json().get("status", "unknown")

        print(
            f"\r{spinner[i % len(spinner)]} status = {status}",
            end="",
            flush=True
        )
        i += 1

        if status == "ready":
            print("\n✅ Metadata layout is READY")
            return

        time.sleep(poll_interval)


def ensure_metadata_layout(checksum: str, disc_type: str, movie: dict):
    payload = {
        "disc_type": disc_type,
        "imdb_id": movie.get("imdbID"),
        "title": movie.get("Title"),
        "year": movie.get("Year"),
    }

    r = requests.post(
        f"{_get_api_url()}/metadata-layout/{checksum}",
        json=payload,
        timeout=5,
    )

    if r.status_code in (200, 201):
        print("🆕 Metadata layout created")
        return

    if r.status_code == 409:
        print("ℹ️ Metadata layout already exists")
        return

    print("❌ Failed to ensure metadata layout")
    print(r.status_code, r.text)
    raise SystemExit(1)