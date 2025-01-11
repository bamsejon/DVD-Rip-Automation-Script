import os
import subprocess

# Paths to tools (adjust these to match your system)
MAKE_MKV_PATH = "/Applications/MakeMKV.app/Contents/MacOS/makemkvcon"  # Path to MakeMKV
HANDBRAKE_CLI_PATH = "/usr/local/bin/HandBrakeCLI"  # Path to HandBrakeCLI

# Output directory (customize this as needed)
OUTPUT_DIR = "/Users/smuel/Desktop/DVD_Output"  # Ensure this directory is writable


def get_titles(disc_index=0):
    """
    Fetch available titles from the DVD using MakeMKV.
    Returns a list of title IDs if successful, or an empty list on failure.
    """
    print("Fetching available titles from the DVD...")
    info_command = [
        MAKE_MKV_PATH,
        "info",
        f"disc:{disc_index}"
    ]
    try:
        result = subprocess.run(info_command, stdout=subprocess.PIPE, text=True, check=True)
        output = result.stdout
        print(output)

        # Parse available titles
        titles = []
        for line in output.splitlines():
            if "Title #" in line:
                title_id = line.split()[1].replace("#", "")
                titles.append(title_id)
        return titles
    except subprocess.CalledProcessError as e:
        print(f"Error during title fetching: {e}")
        return []


def rip_dvd(output_dir, title_id, disc_index=0):
    """
    Rip a specific title from the DVD using MakeMKV.
    """
    print(f"Starting DVD ripping for title {title_id} with MakeMKV...")
    makemkv_command = [
        MAKE_MKV_PATH,
        "mkv",
        f"disc:{disc_index}",
        title_id,
        output_dir
    ]
    try:
        subprocess.run(makemkv_command, check=True)
        print(f"Ripping complete for title {title_id}. Files saved to: {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error during ripping: {e}")
        return False
    return True


def compress_video(input_file, output_file, preset="Fast 1080p30"):
    """
    Compress a video file using HandBrakeCLI.
    """
    print(f"Starting compression of {input_file} with HandBrakeCLI...")
    handbrake_command = [
        HANDBRAKE_CLI_PATH,
        "-i", input_file,  # Input file
        "-o", output_file,  # Output file
        "--preset", preset  # Preset (e.g., Fast 1080p30)
    ]
    try:
        subprocess.run(handbrake_command, check=True)
        print(f"Compression complete. File saved to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during compression: {e}")
        return False
    return True


def main():
    """
    Main workflow for DVD ripping and compression.
    """
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Get available titles
    titles = get_titles()
    if not titles:
        print("No titles found on the disc. Exiting.")
        return

    # Allow user to choose a title (default to the first title)
    print("Available titles:", titles)
    title_id = titles[0]  # Automatically choose the first title
    print(f"Ripping title {title_id}...")

    # Step 2: Rip the DVD
    if not rip_dvd(OUTPUT_DIR, title_id):
        print("Ripping failed. Exiting.")
        return

    # Step 3: Compress the ripped files
    ripped_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mkv")]
    if not ripped_files:
        print("No MKV files found. Ensure the DVD was ripped correctly.")
        return

    for ripped_file in ripped_files:
        input_file = os.path.join(OUTPUT_DIR, ripped_file)
        output_file = os.path.join(OUTPUT_DIR, f"compressed_{ripped_file}")
        if not compress_video(input_file, output_file):
            print(f"Compression failed for {input_file}. Skipping.")


if __name__ == "__main__":
    main()
