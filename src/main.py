import sys
import os
import argparse
import logging
import shutil
from pathlib import Path
from utils import setup_logging, load_config, parse_filename, disable_quick_edit
# from seafile_client import SeafileClient
# from rclone_wrapper import RcloneWrapper
try:
    from seafile_client import SeafileClient
    from rclone_wrapper import RcloneWrapper
except ImportError:
    # For testing in sandbox where we might want to inject mocks or if strict dependencies are missing
    pass

def process_file(file_path: Path, config, seafile, rclone):
    local_root = Path(config['local']['root_path'])
    remote_root = config['rclone']['remote_root']
    library_id = config['seafile']['library_id']
    
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
    std_name = meta['full_name']
    title = meta['title']
    season = meta['season'] # "01", "02", etc.

    # Construct Destination Path: Library / Title / Season XX /
    dest_dir = library_path / title / f"Season {season}"

    # 3. Upload
    # Convert to WebDAV path: "/Videos/Anime/AOT/Ep1.mkv"
    remote_rel_path = rel_path.as_posix()
    remote_full_path = f"{library_id}/{remote_root}/{remote_rel_path}".replace('//', '/')
    remote_parent_dir = os.path.dirname(remote_full_path)

    if not rclone.upload(file_path, remote_parent_dir):
        return

    # 4. Get Link
    link = seafile.get_share_link(remote_full_path)
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
        dest_dir.mkdir(parents=True, exist_ok=True)
        with open(strm_path, "w", encoding='utf-8') as f:
            f.write(strm_content)
        logging.info(f"Generated STRM: {strm_path}")
    except Exception as e:
        logging.error(f"Failed to write STRM: {e}")

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

def process_path_arg(target_path: Path, config, seafile, rclone, video_exts):
    """
    Recursively processes a file or directory.
    """
    if target_path.is_file():
        if target_path.suffix.lower() in video_exts:
            process_file(target_path, config, seafile, rclone)
    elif target_path.is_dir():
        for file_path in target_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_exts:
                process_file(file_path, config, seafile, rclone)


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

    # Parse Args
    parser = argparse.ArgumentParser(description="NAS Seafile Offloader")
    parser.add_argument("paths", nargs='+', help="File or Folder paths passed by qBittorrent or manual selection")
    args = parser.parse_args()
    
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

    # Get extensions from config or default
    video_exts = tuple(config.get('local', {}).get('extensions', ['.mp4', '.mkv', '.avi', '.mov']))
    # Ensure they are lower case
    video_exts = tuple(ext.lower() for ext in video_exts)

    for path_str in args.paths:
        target_path = Path(path_str)
        logging.info(f"Triggered for: {target_path}")

        try:
            process_path_arg(target_path, config, seafile, rclone, video_exts)
        except Exception as e:
            logging.exception(f"Critical error during execution for {target_path}: {e}")
            # Continue with other paths even if one fails
    
    logging.info("Job execution finished.")

if __name__ == "__main__":
    main()
