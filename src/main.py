import sys
import os
import argparse
import logging
from pathlib import Path
from utils import setup_logging, load_config
from seafile_client import SeafileClient
from rclone_wrapper import RcloneWrapper

def process_file(file_path: Path, config, seafile, rclone):
    local_root = Path(config['local']['root_path'])
    remote_root = config['rclone']['remote_root']
    library_id = config['seafile']['library_id']
    col_path = ""
    if 'col_path' in config['seafile']:
        col_path = config['seafile']['col_path']
    
    # 1. Path Mapping
    # Ensure file is within our managed library
    try:
        rel_path = file_path.relative_to(local_root)
    except ValueError:
        logging.warning(f"Skipping: {file_path} (Not in {local_root})")
        return

    # Convert to WebDAV path: "/Videos/Anime/AOT/Ep1.mkv"
    # pathlib handles separators, but for remote WebDAV we usually want forward slashes
    remote_rel_path = rel_path.as_posix()
    remote_full_path = f"{library_id}/{remote_root}/{remote_rel_path}".replace('//', '/')
    remote_parent_dir = os.path.dirname(remote_full_path) # os.path is fine for string manipulation here, or could use str manipulation

    # 2. Upload
    if not rclone.upload(file_path, remote_parent_dir):
        return

    # 3. Get Link
    link = seafile.get_share_link(remote_full_path)
    if not link:
        return

    # 4. Generate .strm
    # Name: "Ep1 [Cloud].strm"
    suffix = config['local'].get('strm_suffix', '')
    strm_path = file_path.with_name(f"{file_path.stem}{suffix}.strm")
    
    
    try:
        with open(strm_path, "w", encoding='utf-8') as f:
            f.write(f"{link}?dl=1")
        if col_path:
            with open(col_path, "w", encoding='utf-8') as f:
            f.write(f"{link}?dl=1")
        logging.info(f"Generated STRM: {strm_path}")
    except Exception as e:
        logging.error(f"Failed to write STRM: {e}")

    # 5. Optional Delete
    if config['local'].get('delete_after_upload', False):
        try:
            file_path.unlink()
            logging.info(f"Deleted local file: {file_path}")
        except OSError as e:
            logging.error(f"Failed to delete local file: {e}")

def main():
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
    parser.add_argument("path", help="File or Folder path passed by qBittorrent")
    args = parser.parse_args()
    
    target_path = Path(args.path)
    
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

    logging.info(f"Triggered for: {target_path}")

    # Get extensions from config or default
    video_exts = tuple(config.get('local', {}).get('extensions', ['.mp4', '.mkv', '.avi', '.mov']))
    # Ensure they are lower case
    video_exts = tuple(ext.lower() for ext in video_exts)

    try:
        # Recursive Processing
        if target_path.is_file():
            if target_path.suffix.lower() in video_exts:
                process_file(target_path, config, seafile, rclone)
        elif target_path.is_dir():
            for file_path in target_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in video_exts:
                    process_file(file_path, config, seafile, rclone)
    except Exception as e:
        logging.exception(f"Critical error during execution: {e}")
    
    logging.info("Job execution finished.")

if __name__ == "__main__":
    main()
