import sys
import os
import argparse
import logging
from utils import setup_logging, load_config
from seafile_client import SeafileClient
from rclone_wrapper import RcloneWrapper

def process_file(file_path, config, seafile, rclone):
    local_root = config['local']['root_path']
    remote_root = config['rclone']['remote_root']
    
    # 1. Path Mapping
    # Ensure file is within our managed library
    if not file_path.startswith(local_root):
        logging.warning(f"Skipping: {file_path} (Not in {local_root})")
        return

    # Calculate relative path: e.g., "Anime\AOT\Ep1.mkv"
    rel_path = os.path.relpath(file_path, local_root)
    
    # Convert to WebDAV path: "/Videos/Anime/AOT/Ep1.mkv"
    remote_rel_path = rel_path.replace("\\", "/")
    remote_full_path = f"{remote_root}/{remote_rel_path}"
    remote_parent_dir = os.path.dirname(remote_full_path)

    # 2. Upload
    if not rclone.upload(file_path, remote_parent_dir):
        return

    # 3. Get Link
    link = seafile.get_share_link(remote_full_path)
    if not link:
        return

    # 4. Generate .strm
    # Name: "Ep1 [Cloud].strm"
    file_name_no_ext = os.path.splitext(file_path)[0]
    suffix = config['local'].get('strm_suffix', '')
    strm_path = f"{file_name_no_ext}{suffix}.strm"
    
    try:
        with open(strm_path, "w", encoding='utf-8') as f:
            f.write(f"{link}?dl=1")
        logging.info(f"Generated STRM: {strm_path}")
    except Exception as e:
        logging.error(f"Failed to write STRM: {e}")

    # 5. Optional Delete
    if config['local'].get('delete_after_upload', False):
        try:
            os.remove(file_path)
            logging.info(f"Deleted local file: {file_path}")
        except OSError as e:
            logging.error(f"Failed to delete local file: {e}")

def main():
    # Setup
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    setup_logging(os.path.join(root_dir, "logs"))
    config = load_config(os.path.join(root_dir, "config", "config.yaml"))

    # Parse Args
    parser = argparse.ArgumentParser(description="NAS Seafile Offloader")
    parser.add_argument("path", help="File or Folder path passed by qBittorrent")
    args = parser.parse_args()
    
    target_path = args.path
    
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

    # Recursive Processing
    if os.path.isfile(target_path):
        if target_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            process_file(target_path, config, seafile, rclone)
    elif os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                    process_file(os.path.join(root, file), config, seafile, rclone)
    
    logging.info("Job execution finished.")

if __name__ == "__main__":
    main()