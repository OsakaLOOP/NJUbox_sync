import requests
from urllib.parse import urljoin
import logging

class SeafileClient:
    def __init__(self, host, token, repo_id=None, repo_name=None):
        self.host = host
        self.headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
        self.repo_name = repo_name
        self.repo_id = None

        if self.repo_name:
            try:
                found_id = self.get_repo_id_by_name(self.repo_name)
                if found_id:
                    self.repo_id = found_id
                    logging.info(f"Resolved repo_name '{self.repo_name}' to repo_id '{self.repo_id}'")
                else:
                    logging.warning(f"Could not find repo with name '{self.repo_name}' and permission 'rw'.")
            except Exception as e:
                 logging.error(f"Error during repo lookup: {e}")

        # Fallback or primary use of repo_id
        if not self.repo_id and repo_id:
            self.repo_id = repo_id
            if self.repo_name:
                 logging.info(f"Falling back to provided repo_id '{self.repo_id}'")

        if not self.repo_id:
            raise ValueError("Could not determine repo_id. Please provide a valid repo_id or a reachable repo_name.")

    def get_repos(self):
        """Fetches the list of repositories from the API."""
        url = urljoin(self.host, "/api/v2.1/repos/")
        resp = requests.get(url, headers=self.headers)
        if not resp.ok:
            logging.error(f"Failed to list repos. Status: {resp.status_code}, Body: {resp.text}")
            resp.raise_for_status()
        return resp.json()

    def get_repo_id_by_name(self, target_name):
        """
        Finds a repo ID by name from the API response.
        Ensures permission is 'rw'.
        """
        data = self.get_repos()

        # Handle if response is dict with 'repos' key or just a list
        repos = []
        if isinstance(data, dict):
            repos = data.get('repos', [])
        elif isinstance(data, list):
            repos = data
        else:
            logging.error(f"Unexpected API response format: {type(data)}")
            return None

        for repo in repos:
            # Check for name match and write permission
            if repo.get('repo_name') == target_name and repo.get('permission') == 'rw':
                return repo.get('repo_id')

        return None

    def get_share_link(self, remote_path):
        """Generates or retrieves a direct download link."""

        # Adjust path if repo_name is known and path starts with it
        # This handles the case where Rclone remote root includes the repo name
        if self.repo_name:
            prefix = f"/{self.repo_name}"
            # Check for "/RepoName" (exact) or "/RepoName/..."
            if remote_path == prefix or remote_path.startswith(f"{prefix}/"):
                # Strip the prefix
                original_path = remote_path
                remote_path = remote_path[len(prefix):]
                if not remote_path.startswith("/"):
                    remote_path = "/" + remote_path
                logging.info(f"Adjusted path from '{original_path}' to '{remote_path}' based on repo_name")

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
