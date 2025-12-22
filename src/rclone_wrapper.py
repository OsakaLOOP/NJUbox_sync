import subprocess
import logging
import os

class RcloneWrapper:
    def __init__(self, remote_name, bandwidth_limit="5M"):
        self.remote_name = remote_name
        self.bwlimit = bandwidth_limit

    def upload(self, local_path, remote_dir):
        """
        Uploads file to remote using Rclone.
        Returns True if successful, False otherwise.
        """
        # cmd: rclone copy "C:\..." "remote:/dir" --bwlimit 5M --transfers 2 --ignore-existing
        cmd = [
            "rclone", "copy", local_path,
            f"{self.remote_name}:{remote_dir}",
            "--bwlimit", self.bwlimit,
            "--transfers", "2",
            "--ignore-existing" 
        ]

        logging.info(f"Rclone uploading: {local_path} -> {remote_dir}")

        # Hide console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            result = subprocess.call(cmd, startupinfo=startupinfo)
            if result == 0:
                return True
            else:
                logging.error(f"Rclone exited with code {result}")
                return False
        except FileNotFoundError:
            logging.error("Rclone executable not found in PATH.")
            return False