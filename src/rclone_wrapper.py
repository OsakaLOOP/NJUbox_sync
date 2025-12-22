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
            "rclone", "copy", str(local_path),
            f"{self.remote_name}:{remote_dir}",
            "--bwlimit", self.bwlimit,
            "--transfers", "2",
            "--ignore-existing","--progress"
        ]

        logging.info(f"Rclone uploading: {local_path} -> {remote_dir}")

        # Hide console window on Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            # Use subprocess.run for better control and output capturing if needed
            result = subprocess.run(
                cmd,
                startupinfo=startupinfo,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return True
            else:
                logging.error(f"Rclone failed with code {result.returncode}")
                logging.error(f"Stderr: {result.stderr}")
                return False
        except FileNotFoundError:
            logging.error("Rclone executable not found in PATH.")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during rclone execution: {e}")
            return False
