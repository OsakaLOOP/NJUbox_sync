import requests
import logging
import time

class AniListClient:
    def __init__(self):
        self.url = 'https://graphql.anilist.co'
        self.query = '''
        query ($search: String) {
          Media (search: $search, type: ANIME, sort: SEARCH_MATCH) {
            id
            title {
              romaji
              english
              native
            }
            description
            coverImage {
              large
            }
            season
            seasonYear
            episodes
            status
            genres
            averageScore
            studios(isMain: true) {
              nodes {
                name
              }
            }
            startDate {
              year
              month
              day
            }
          }
        }
        '''

    def search_anime(self, title: str):
        """
        Searches for an anime by title on AniList.
        """
        variables = {'search': title}

        try:
            # Respect rate limits (simple approach)
            time.sleep(0.5)

            response = requests.post(self.url, json={'query': self.query, 'variables': variables}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'Media' in data['data']:
                    return data['data']['Media']
                else:
                    logging.warning(f"AniList: No results found for '{title}'")
                    return None
            elif response.status_code == 404:
                logging.warning(f"AniList: 404 Not Found for '{title}'")
                return None
            else:
                logging.error(f"AniList API Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logging.error(f"AniList connection failed: {e}")
            return None
