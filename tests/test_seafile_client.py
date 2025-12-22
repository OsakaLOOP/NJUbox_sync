import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import requests

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from seafile_client import SeafileClient

class TestSeafileClient(unittest.TestCase):
    def setUp(self):
        self.client = SeafileClient("http://seafile.example.com", "token123", "repo123")

    @patch('requests.post')
    def test_get_share_link_create_success(self, mock_post):
        # Setup
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'link': 'http://link.com/xyz'}
        mock_post.return_value = mock_resp

        # Execute
        link = self.client.get_share_link("/foo.mkv")

        # Assert
        self.assertEqual(link, 'http://link.com/xyz')
        mock_post.assert_called_once()

    @patch('requests.get')
    @patch('requests.post')
    def test_get_share_link_exists_fallback(self, mock_post, mock_get):
        # Setup Post -> 400
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 400
        mock_post_resp.ok = False
        mock_post_resp.text = '{"error_msg": "Link exists"}'
        mock_post.return_value = mock_post_resp

        # Setup Get -> 200 with list
        mock_get_resp = MagicMock()
        mock_get_resp.ok = True
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = [{'link': 'http://link.com/existing'}]
        mock_get.return_value = mock_get_resp

        # Execute
        link = self.client.get_share_link("/foo.mkv")

        # Assert
        self.assertEqual(link, 'http://link.com/existing')
        mock_post.assert_called_once()
        mock_get.assert_called_once()

    @patch('requests.post')
    def test_get_share_link_fail_logs_error(self, mock_post):
        # Setup
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error", response=mock_resp)
        mock_post.return_value = mock_resp

        # Execute
        with self.assertLogs(level='ERROR') as log:
            link = self.client.get_share_link("/foo.mkv")

        # Assert
        self.assertIsNone(link)
        self.assertTrue(any("Internal Server Error" in output for output in log.output))

    @patch('requests.get')
    @patch('requests.post')
    def test_get_share_link_fallback_fail(self, mock_post, mock_get):
        # Setup Post -> 400
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 400
        mock_post_resp.text = "Link exists"
        mock_post.return_value = mock_post_resp

        # Setup Get -> 500
        mock_get_resp = MagicMock()
        mock_get_resp.ok = False
        mock_get_resp.status_code = 500
        mock_get_resp.text = "Get failed"
        mock_get_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Get Error", response=mock_get_resp)
        mock_get.return_value = mock_get_resp

        # Execute
        with self.assertLogs(level='ERROR') as log:
            link = self.client.get_share_link("/foo.mkv")

        # Assert
        self.assertIsNone(link)
        self.assertTrue(any("Get failed" in output for output in log.output))
