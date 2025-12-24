import shutil
import logging
from pathlib import Path
from utils import generate_tvshow_nfo, save_image, sanitize_filename
from anilist_client import AniListClient

def migrate_legacy_library(library_path: Path, anilist_client: AniListClient):
    """
    Scans the library_path for folders that are NOT "Anime".
    Moves them into library_path / "Anime" / [Canonical Title] / ...
    Generates NFOs and cover art.
    """
    if not library_path.exists():
        logging.warning(f"Library path {library_path} does not exist. Skipping migration.")
        return

    anime_root = library_path / "Anime"
    anime_root.mkdir(exist_ok=True)

    # Iterate over items in library_path
    for item in library_path.iterdir():
        if item.name == "Anime":
            continue

        if not item.is_dir():
            # Skip loose files in root (or handle them if needed, but current logic implies series folders)
            continue

        # Found a potential legacy series folder
        legacy_name = item.name
        logging.info(f"Migration: Found legacy folder '{legacy_name}'")

        # 1. Identify Series
        metadata = anilist_client.search_anime(legacy_name)
        if metadata:
            canonical_title = metadata['title']['english'] or metadata['title']['romaji']
            # Sanitize for filesystem
            canonical_title = sanitize_filename(canonical_title)
            logging.info(f"Migration: Identified '{legacy_name}' as '{canonical_title}'")
        else:
            logging.warning(f"Migration: Could not identify '{legacy_name}'. Moving as is.")
            canonical_title = sanitize_filename(legacy_name)
            metadata = None # Cannot generate full NFO

        # 2. Target Directory
        target_series_dir = anime_root / canonical_title
        target_series_dir.mkdir(exist_ok=True)

        # 3. Move Contents
        # We need to merge contents if target already exists
        for sub_item in item.iterdir():
            dest = target_series_dir / sub_item.name
            try:
                if dest.exists():
                     # Conflict resolution: if dir, merge? if file, overwrite or skip?
                     # Simple approach: skip if exists, log warning
                    if sub_item.is_dir() and dest.is_dir():
                        # Recursively move/merge content?
                        # For now, let's just use shutil.move which might fail if dest exists
                        # Better: iterate deeper or rename source
                        logging.warning(f"Migration: Destination {dest} already exists. Skipping merge for {sub_item.name}")
                    else:
                        logging.warning(f"Migration: File {dest} already exists. Skipping {sub_item.name}")
                else:
                    shutil.move(str(sub_item), str(dest))
            except Exception as e:
                logging.error(f"Migration: Failed to move {sub_item} to {dest}: {e}")

        # 4. Generate Metadata (NFO / Images)
        if metadata:
            generate_tvshow_nfo(metadata, target_series_dir)
            if metadata.get('coverImage') and metadata['coverImage'].get('large'):
                # Save as poster.jpg
                save_image(metadata['coverImage']['large'], target_series_dir / "poster.jpg")
                # Also save as folder.jpg for Windows/some players
                save_image(metadata['coverImage']['large'], target_series_dir / "folder.jpg")

        # 5. Clean up old folder
        try:
            # Only remove if empty
            item.rmdir()
            logging.info(f"Migration: Removed empty legacy folder '{legacy_name}'")
        except OSError:
            logging.warning(f"Migration: Could not remove '{legacy_name}' (not empty?)")
