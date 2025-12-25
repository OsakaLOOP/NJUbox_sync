import logging
import logging.handlers
import sys
import io
import os
import shutil
import subprocess
import yaml
import anitopy
import ctypes
import re
import requests
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

def generate_thumbnail(input_path: str, output_path: str):
    """
    Generates a thumbnail for the video file using FFmpeg.
    Takes a frame at 10 seconds.
    """
    ffmpeg_cmd = shutil.which('ffmpeg')
    if not ffmpeg_cmd:
        logging.warning("FFmpeg not found. Skipping thumbnail generation.")
        return

    try:
        # ffmpeg -i input -ss 00:00:10 -vframes 1 output.jpg -y
        cmd = [
            ffmpeg_cmd,
            '-i', str(input_path),
            '-ss', '00:00:10',
            '-vframes', '1',
            str(output_path),
            '-y'
        ]

        # Run ffmpeg, suppress output unless error
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.info(f"Generated Thumbnail: {output_path}")
            else:
                logging.error(f"FFmpeg ran but thumbnail file is empty or missing: {output_path}")
        else:
            logging.error(f"FFmpeg failed: {result.stderr}")

    except Exception as e:
        logging.error(f"Error generating thumbnail: {e}")

def save_image(url: str, output_path: str):
    """
    Downloads and saves an image from a URL.
    """
    if not url:
        return

    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            logging.info(f"Saved image: {output_path}")
        else:
            logging.error(f"Failed to download image {url}: Status {response.status_code}")
    except Exception as e:
        logging.error(f"Error downloading image {url}: {e}")

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def generate_tvshow_nfo(metadata: dict, output_dir: Path):
    """
    Generates tvshow.nfo for Jellyfin/Kodi.
    metadata: dict from AniListClient
    """
    if not metadata:
        return

    root = ET.Element("tvshow")

    # Title
    title_node = ET.SubElement(root, "title")
    title_node.text = metadata['title']['english'] or metadata['title']['romaji'] or metadata['title']['native']

    # Original Title
    if metadata['title']['native']:
        orig_title = ET.SubElement(root, "originaltitle")
        orig_title.text = metadata['title']['native']

    # Plot
    if metadata.get('description'):
        plot = ET.SubElement(root, "plot")
        # Remove HTML tags if present (simple replace)
        desc = metadata['description'].replace('<br>', '\n').replace('<i>', '').replace('</i>', '')
        plot.text = desc

    # Year / Premiered
    if metadata.get('startDate'):
        date_str = f"{metadata['startDate'].get('year')}-{metadata['startDate'].get('month', 1):02d}-{metadata['startDate'].get('day', 1):02d}"
        premiered = ET.SubElement(root, "premiered")
        premiered.text = date_str
        year = ET.SubElement(root, "year")
        year.text = str(metadata['startDate'].get('year'))

    # Rating
    if metadata.get('averageScore'):
        rating = ET.SubElement(root, "rating")
        rating.text = str(metadata['averageScore'] / 10.0)

    # Studio
    if metadata.get('studios') and metadata['studios'].get('nodes'):
        studio = ET.SubElement(root, "studio")
        studio.text = metadata['studios']['nodes'][0]['name']

    # Genre
    if metadata.get('genres'):
        for g in metadata['genres']:
            genre = ET.SubElement(root, "genre")
            genre.text = g

    # Status
    if metadata.get('status'):
        status = ET.SubElement(root, "status")
        status.text = metadata['status']

    # Unique ID (AniList)
    uniqueid = ET.SubElement(root, "uniqueid", type="anilist", default="true")
    uniqueid.text = str(metadata['id'])

    # Write file
    nfo_path = output_dir / "tvshow.nfo"
    try:
        with open(nfo_path, "w", encoding='utf-8') as f:
            f.write(prettify_xml(root))
        logging.info(f"Generated NFO: {nfo_path}")
    except Exception as e:
        logging.error(f"Failed to generate tvshow.nfo: {e}")

def generate_episode_nfo(metadata: dict, episode_num: str, season_num: str, output_path: Path):
    """
    Generates episode .nfo
    Currently just basic info as we don't fetch per-episode data.
    """
    root = ET.Element("episodedetails")

    title_node = ET.SubElement(root, "title")
    # We don't have episode title, so use generic
    title_node.text = f"Episode {episode_num}"

    season = ET.SubElement(root, "season")
    season.text = str(int(season_num))

    episode = ET.SubElement(root, "episode")
    episode.text = str(episode_num)

    # Link to show
    showtitle = ET.SubElement(root, "showtitle")
    showtitle.text = metadata['title']['english'] or metadata['title']['romaji']

    try:
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(prettify_xml(root))
        logging.info(f"Generated Episode NFO: {output_path}")
    except Exception as e:
        logging.error(f"Failed to generate episode nfo: {e}")

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to be safe for use as a filename on Windows.
    Removes: < > : " / \\ | ? *
    """
    # Replace illegal characters with underscore or nothing
    # < > : " / \ | ? *
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def disable_quick_edit():
    """
    Disables Quick Edit Mode in Windows Command Prompt to prevent
    pausing execution when clicking in the console.
    """
    if sys.platform == 'win32':
        try:
            kernel32 = ctypes.windll.kernel32
            # ENABLE_QUICK_EDIT_MODE = 0x0040
            # ENABLE_EXTENDED_FLAGS = 0x0080
            # ENABLE_INSERT_MODE = 0x0020
            # ENABLE_MOUSE_INPUT = 0x0010
            # We want to remove QUICK_EDIT and INSERT mode.

            # Get current console mode
            hStdIn = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE = -10
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(hStdIn, ctypes.byref(mode)):
                return

            # Disable Quick Edit (0x0040) and Insert Mode (0x0020)
            # We must preserve ENABLE_EXTENDED_FLAGS (0x0080) to allow setting these
            new_mode = mode.value
            new_mode &= ~0x0040 # turn off quick edit
            new_mode &= ~0x0020 # turn off insert mode (optional but good)
            new_mode |= 0x0080  # set extended flags

            kernel32.SetConsoleMode(hStdIn, new_mode)
        except Exception as e:
            # Don't let this crash the app
            print(f"Failed to disable Quick Edit mode: {e}", file=sys.stderr)

def parse_filename(filename: str) -> dict:
    """
    Parses a filename using anitopy and returns standardized metadata.
    Returns a dict with:
        - title: Series Title
        - season: Season Number (formatted string "01", "02")
        - episode: Episode Number (string)
        - full_name: Standardized Name (e.g. "Title - S01E01")
        - original_name: The input filename
    """
    data = anitopy.parse(filename)

    title_raw = data.get('anime_title', filename)
    title = sanitize_filename(title_raw)

    # Handle Season
    season_raw = data.get('anime_season', '1')
    try:
        if isinstance(season_raw, list):
             season_val = int(season_raw[0])
        else:
             season_val = int(season_raw)
        season_str = f"{season_val:02d}"
    except (ValueError, TypeError):
        season_str = "01"

    # Handle Episode
    episode_raw = data.get('episode_number', '')
    if isinstance(episode_raw, list):
         episode_raw = episode_raw[0]

    # Construct Standardized Name
    # Format: "Title - SxxEyy"
    if episode_raw:
        std_name = f"{title} - S{season_str}E{episode_raw}"
    else:
        # Fallback if no episode number (e.g. movie)
        std_name = title

    return {
        'title': title,
        'season': season_str,
        'episode': episode_raw,
        'full_name': std_name,
        'original_name': filename
    }

def setup_logging(log_dir="logs", log_level="INFO", max_bytes=5*1024*1024, backup_count=3):
    log_dir = str(log_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Windows console encoding fix
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except AttributeError:
             # In case sys.stdout is replaced or doesn't have buffer (e.g. during tests)
            pass

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create handlers
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler]
    )

def load_config(config_path="config/config.yaml"):
    if not os.path.exists(config_path):
        # Fallback to print if logging isn't set up yet, or rely on implicit basicConfig
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
