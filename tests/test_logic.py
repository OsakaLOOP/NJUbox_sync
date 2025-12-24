import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure src is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import main as main_module

class TestPathLogic(unittest.TestCase):
    def setUp(self):
        self.config = {
            'local': {
                'root_path': '/local/root',
                'library_path': '/local/library'
            },
            'rclone': {
                'remote_root': 'RemoteVideos'
            },
            'seafile': {
                'library_id': 'repo-id-123'
            }
        }
        self.seafile_mock = MagicMock()
        self.rclone_mock = MagicMock()
        self.rclone_mock.upload.return_value = True
        self.seafile_mock.get_share_link.return_value = "http://seafile/link"
        self.anilist_mock = MagicMock()
        self.anilist_mock.search_anime.return_value = None
        self.db_mock = MagicMock()

    @patch('main.generate_thumbnail')
    @patch('main.parse_filename')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.iterdir')  # Mock iterdir to prevent filesystem access
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_process_file_paths(self, mock_open, mock_iterdir, mock_mkdir, mock_parse, mock_gen_thumb):
        # Setup
        file_path = Path('/local/root/Anime/Show/file.mkv')
        mock_iterdir.return_value = [] # Return empty list for sibling search

        # Mock filename parsing
        mock_parse.return_value = {
            'full_name': 'Show - S01E01',
            'title': 'Show',
            'season': '01',
            'episode': '01',
            'original_name': 'file.mkv'
        }

        # Run
        main_module.process_file(file_path, self.config, self.seafile_mock, self.rclone_mock, self.anilist_mock, self.db_mock)

        # Assertions for Rclone Path (Step 1 requirement)
        # Expected: rclone destination should NOT have repo_id
        # remote_rel_path = Anime/Show/file.mkv
        # rclone_dest_dir = dirname(RemoteVideos/Anime/Show/file.mkv) -> RemoteVideos/Anime/Show

        self.rclone_mock.upload.assert_called_once()
        args, _ = self.rclone_mock.upload.call_args
        uploaded_path, dest_dir = args

        self.assertEqual(uploaded_path, file_path)
        # Verify repo_id is NOT in the destination
        self.assertEqual(dest_dir, 'RemoteVideos/Anime/Show')
        self.assertNotIn('repo-id-123', dest_dir)

        # Assertions for Seafile Path
        # Expected: seafile path SHOULD NOT have repo_id
        self.seafile_mock.get_share_link.assert_called_once()
        call_arg = self.seafile_mock.get_share_link.call_args[0][0]

        expected_seafile_path = 'RemoteVideos/Anime/Show/file.mkv'
        self.assertEqual(call_arg, expected_seafile_path)

        # Verify DB interaction
        self.db_mock.upsert_mapping.assert_called_once()
        args, _ = self.db_mock.upsert_mapping.call_args
        # args: file_path, strm_path, link, status, info
        self.assertEqual(args[3], 'FAILED') # Because anilist return is None in this test
        self.assertIn('Not found', args[4])

    @patch('main.generate_thumbnail')
    @patch('main.parse_filename')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.iterdir')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_thumbnail_call(self, mock_open, mock_iterdir, mock_mkdir, mock_parse, mock_gen_thumb):
        file_path = Path('/local/root/Movie.mkv')
        mock_iterdir.return_value = []
        mock_parse.return_value = {
            'full_name': 'Movie',
            'title': 'Movie',
            'season': '01',
            'episode': '',
            'original_name': 'Movie.mkv'
        }

        main_module.process_file(file_path, self.config, self.seafile_mock, self.rclone_mock, self.anilist_mock, self.db_mock)

        # Check if thumbnail generation was called with correct path
        mock_gen_thumb.assert_called_once()
        input_arg, output_arg = mock_gen_thumb.call_args[0]

        self.assertEqual(input_arg, file_path)
        self.assertEqual(output_arg, Path('/local/library/Anime/Movie/Season 01/Movie.jpg'))

if __name__ == '__main__':
    unittest.main()
