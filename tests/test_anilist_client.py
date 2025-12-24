import unittest
from src.anilist_client import AniListClient

class TestAniListClient(unittest.TestCase):
    def test_search_anime(self):
        client = AniListClient()
        # Search for a known anime
        result = client.search_anime("Frieren")

        self.assertIsNotNone(result)
        self.assertEqual(result['title']['romaji'], "Sousou no Frieren")
        self.assertIn('Adventure', result['genres'])
        self.assertIsNotNone(result['coverImage']['large'])

if __name__ == '__main__':
    unittest.main()
