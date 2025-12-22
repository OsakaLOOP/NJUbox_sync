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
        url = urljoin(self.host, "/api/v2.1/share-links/")
        
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
                logging.warning(f"Create link returned 400. Response: {resp.text}")
                logging.info(f"Link likely exists for {remote_path}, fetching existing...")

                get_params = {"repo_id": self.repo_id, "path": remote_path}
                get_resp = requests.get(url, headers=self.headers, params=get_params)

                if not get_resp.ok:
                    logging.error(f"Failed to fetch existing links. Status: {get_resp.status_code}, Body: {get_resp.text}")
                    get_resp.raise_for_status()

                links_data = get_resp.json()
                if not links_data:
                    logging.error(f"No share links found for {remote_path} despite 400 error.")
                    logging.error(f"Get existing links response body: {get_resp.text}")
                    return None

                # Return the first link found
                link = links_data[0]['link']
                return link

            if not resp.ok:
                logging.error(f"Failed to create link. Status: {resp.status_code}, Body: {resp.text}")
                resp.raise_for_status()

            return resp.json()['link']
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Seafile API Request Failed: {e}")
            if e.response is not None:
                logging.error(f"Error Response Body: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"Unexpected Seafile Client Error: {e}")
            return None
