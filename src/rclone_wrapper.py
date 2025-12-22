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

        try:
            # Use subprocess.run without capturing output to allow direct console access
            # and prevent pipe buffer deadlocks with large --progress output.
            result = subprocess.run(
                cmd
            )

            if result.returncode == 0:
                return True
            else:
                logging.error(f"Rclone failed with code {result.returncode}")
                # Stderr is not captured, so we direct the user to look at the console
                logging.error("Check console output for error details.")
                return False
        except FileNotFoundError:
            logging.error("Rclone executable not found in PATH.")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during rclone execution: {e}")
            return False
