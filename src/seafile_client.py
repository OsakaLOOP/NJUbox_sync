import requests
from urllib.parse import urljoin
import logging

class SeafileClient:
    def __init__(self, host, token, repo_id):
        self.host = host
        self.headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
        self.repo_id = repo_id

    def get_share_link(self, remote_path):
        """Generates or retrieves a direct download link."""
        url = urljoin(self.host, "/api2/share-links/")
        
        # Payload for creating a link
        payload = {
            "repo_id": self.repo_id,
            "path": remote_path,
            "permissions": {"can_download": True}
        }

        try:
            # Try to create a new link
            resp = requests.post(url, headers=self.headers, data=payload)
            
            # If link already exists (400 Bad Request with specific msg), fetch it
            if resp.status_code == 400:
                logging.info(f"Link likely exists for {remote_path}, fetching existing...")
                get_params = {"repo_id": self.repo_id, "path": remote_path}
                get_resp = requests.get(url, headers=self.headers, params=get_params)
                get_resp.raise_for_status()
                # Return the first link found
                link = get_resp.json()[0]['link']
                return link

            resp.raise_for_status()
            return resp.json()['link']
            
        except Exception as e:
            logging.error(f"Seafile API Error: {e}")
            return None