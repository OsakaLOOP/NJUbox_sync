import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import utils

class TestUtils(unittest.TestCase):
    @patch('logging.basicConfig')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_setup_logging_creates_dir(self, mock_exists, mock_makedirs, mock_stream, mock_file, mock_basic_config):
        mock_exists.return_value = False

        utils.setup_logging("test_logs")

        mock_makedirs.assert_called_with("test_logs")
        mock_basic_config.assert_called()

    @patch('logging.basicConfig')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_setup_logging_exists(self, mock_exists, mock_makedirs, mock_stream, mock_file, mock_basic_config):
        mock_exists.return_value = True

        utils.setup_logging("test_logs")

        mock_makedirs.assert_not_called()
        mock_basic_config.assert_called()
