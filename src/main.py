import sys
import os
import argparse
import logging
import shutil
import json
from pathlib import Path
from utils import setup_logging, load_config, parse_filename, disable_quick_edit, generate_thumbnail, generate_tvshow_nfo, generate_episode_nfo, save_image, sanitize_filename
from seafile_client import SeafileClient
from rclone_wrapper import RcloneWrapper
from anilist_client import AniListClient
from migration import migrate_legacy_library
from database import VideoMappingDB

def prune_mappings(db: VideoMappingDB):
    """
    Checks all mappings in the database.
    If the source file no longer exists, delete the mapping and the generated strm file.
    """
    logging.info("Starting Prune Operation...")
    count = 0
    # Collect removals first to avoid modifying while iterating
    to_remove = []

    for source_path_str, strm_path_str in db.get_all_mappings():
        source_path = Path(source_path_str)
        strm_path = Path(strm_path_str)

        if not source_path.exists():
            logging.info(f"Pruning orphaned mapping: {source_path}")
            to_remove.append(source_path_str)

            # Delete .strm file if it exists
            if strm_path.exists():
                try:
                    strm_path.unlink()
                    logging.info(f"Deleted orphaned strm: {strm_path}")
                except OSError as e:
                    logging.error(f"Failed to delete {strm_path}: {e}")

            # We could also delete thumbnails/subtitles if we tracked them or guessed them
            # For now, just strm is safe.

    for src in to_remove:
        db.delete_mapping(src)
        count += 1

    logging.info(f"Prune finished. Removed {count} orphaned mappings.")

def process_file(file_path: Path, config, seafile, rclone, anilist_client, db: VideoMappingDB):
    local_root = Path(config['local']['root_path'])
    remote_root = config['rclone']['remote_root']
    
    # Check for library_path
    library_path_str = config['local'].get('library_path')
    if not library_path_str:
        logging.error("Missing 'library_path' in config['local']. Cannot proceed with standardization.")
        return
    library_path = Path(library_path_str)

    # 1. Path Mapping
    # Ensure file is within our managed library
    try:
        rel_path = file_path.relative_to(local_root)
    except ValueError:
        logging.warning(f"Skipping: {file_path} (Not in {local_root})")
        return

    # 2. Standardization Analysis
    # Parse filename using anitopy
    meta = parse_filename(file_path.name)

    # AniList Lookup
    anilist_meta = anilist_client.search_anime(meta['title'])

    if anilist_meta:
        canonical_title = anilist_meta['title']['english'] or anilist_meta['title']['romaji'] or meta['title']
        canonical_title = sanitize_filename(canonical_title)
        series_dir_name = canonical_title

        meta_status = 'SUCCESS'
        meta_info = json.dumps({
            'id': anilist_meta.get('id'),
            'title_en': anilist_meta['title'].get('english'),
            'title_ro': anilist_meta['title'].get('romaji'),
            'canonical': canonical_title
        })
    else:
        series_dir_name = meta['title']

        meta_status = 'FAILED'
        meta_info = json.dumps({
            'error': 'Not found',
            'query': meta['title']
        })

    std_name = meta['full_name']

    # Construct Destination Path: Library / Anime / Canonical Title / Season XX /
    dest_dir = library_path / "Anime" / series_dir_name / f"Season {meta['season']}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate Series NFO if AniList data found (and not exists)
    if anilist_meta:
        if not (dest_dir.parent / "tvshow.nfo").exists():
             generate_tvshow_nfo(anilist_meta, dest_dir.parent)

        # Download cover art if missing
        poster_path = dest_dir.parent / "poster.jpg"
        if not poster_path.exists() and anilist_meta.get('coverImage') and anilist_meta['coverImage'].get('large'):
             save_image(anilist_meta['coverImage']['large'], poster_path)
             # Also folder.jpg
             save_image(anilist_meta['coverImage']['large'], dest_dir.parent / "folder.jpg")

    # 3. Upload
    # Convert to WebDAV path: "/Videos/Anime/AOT/Ep1.mkv"
    remote_rel_path = rel_path.as_posix().lstrip('/')

    # Path for Seafile API
    seafile_path = f"{remote_root}/{remote_rel_path}".replace('//', '/')

    # Path for Rclone (excludes library_id)
    # Using parent directory for rclone destination to match "rclone copy file dest_dir" behavior
    rclone_dest_dir = os.path.dirname(f"{remote_root}/{remote_rel_path}".replace('//', '/'))

    if not rclone.upload(file_path, rclone_dest_dir):
        return

    # 4. Get Link
    link = seafile.get_share_link(seafile_path)
    if not link:
        return

    # 5. Generate .strm
    # Content: link + fragment
    # Fragment: #StandardizedName.OriginalExt
    fragment = f"#{std_name}{file_path.suffix}"
    strm_content = f"{link}?dl=1{fragment}"
    
    strm_filename = f"{std_name}.strm"
    strm_path = dest_dir / strm_filename
    
    try:
        with open(strm_path, "w", encoding='utf-8') as f:
            f.write(strm_content)
        logging.info(f"Generated STRM: {strm_path}")

        # Save mapping to DB
        db.upsert_mapping(file_path, strm_path, link, meta_status, meta_info)

    except Exception as e:
        logging.error(f"Failed to write STRM: {e}")

    # 5a. Generate Thumbnail
    thumb_filename = f"{std_name}.jpg"
    thumb_path = dest_dir / thumb_filename
    generate_thumbnail(file_path, thumb_path)

    # 5b. Generate Episode NFO
    if anilist_meta:
        nfo_filename = f"{std_name}.nfo"
        nfo_path = dest_dir / nfo_filename
        generate_episode_nfo(anilist_meta, meta['episode'], meta['season'], nfo_path)

    # 6. Handle Subtitles
    # Look for files with same stem in source dir
    # Common subtitle exts
    sub_exts = {'.ass', '.srt', '.sub', '.vtt'}

    # Iterate over files in the same directory as the video
    # Strategy: Find files where file.stem == file_path.stem and suffix in sub_exts
    for sibling in file_path.parent.iterdir():
        if sibling.is_file() and sibling.stem == file_path.stem and sibling.suffix.lower() in sub_exts:
            # Found subtitle
            sub_dest_name = f"{std_name}{sibling.suffix}"
            sub_dest_path = dest_dir / sub_dest_name
            try:
                shutil.copy2(sibling, sub_dest_path)
                logging.info(f"Copied Subtitle: {sibling} -> {sub_dest_path}")
            except Exception as e:
                logging.error(f"Failed to copy subtitle {sibling}: {e}")

    # 7. Optional Delete
    if config['local'].get('delete_after_upload', False):
        try:
            file_path.unlink()
            logging.info(f"Deleted local file: {file_path}")
        except OSError as e:
            logging.error(f"Failed to delete local file: {e}")

def process_path_arg(target_path: Path, config, seafile, rclone, anilist_client, video_exts, db: VideoMappingDB):
    """
    Recursively processes a file or directory.
    """
    if target_path.is_file():
        if target_path.suffix.lower() in video_exts:
            process_file(target_path, config, seafile, rclone, anilist_client, db)
    elif target_path.is_dir():
        for file_path in target_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_exts:
                process_file(file_path, config, seafile, rclone, anilist_client, db)


def main():
    # Disable Quick Edit Mode (Windows)
    disable_quick_edit()

    # Setup
    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / "config" / "config.yaml"

    # Load config first to get log settings
    config = load_config(str(config_path))

    # Setup logging with config
    log_level = config.get('log_level', 'INFO')
    setup_logging(str(root_dir / "logs"), log_level=log_level)

    # Init DB
    db_path = root_dir / "data" / "video_map.db"
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
    db = VideoMappingDB(str(db_path))

    # Parse Args
    parser = argparse.ArgumentParser(description="NAS Seafile Offloader")
    parser.add_argument("paths", nargs='*', help="File or Folder paths passed by qBittorrent or manual selection")
    parser.add_argument("--prune", action="store_true", help="Remove orphaned strm files for deleted source files")
    args = parser.parse_args()
    
    # Handle Prune
    if args.prune:
        prune_mappings(db)

    # Init Clients
    seafile = SeafileClient(
        config['seafile']['host'],
        config['seafile']['api_token'],
        config['seafile']['repo_id']
    )
    rclone = RcloneWrapper(
        config['rclone']['remote_name'],
        config['rclone']['bwlimit']
    )

    anilist_client = AniListClient()

    # Migration Check
    # Check if migration is needed (files outside /Anime)
    # We do this once at startup
    library_path_str = config['local'].get('library_path')
    if library_path_str:
        try:
             migrate_legacy_library(Path(library_path_str), anilist_client)
        except Exception as e:
             logging.error(f"Migration failed: {e}")

    # Get extensions from config or default
    video_exts = tuple(config.get('local', {}).get('extensions', ['.mp4', '.mkv', '.avi', '.mov']))
    # Ensure they are lower case
    video_exts = tuple(ext.lower() for ext in video_exts)

    for path_str in args.paths:
        target_path = Path(path_str)
        logging.info(f"Triggered for: {target_path}")

        try:
            process_path_arg(target_path, config, seafile, rclone, anilist_client, video_exts, db)
        except Exception as e:
            logging.exception(f"Critical error during execution for {target_path}: {e}")
            # Continue with other paths even if one fails
    
    logging.info("Job execution finished.")

if __name__ == "__main__":
    main()
