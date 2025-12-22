import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import utils

class TestUtils(unittest.TestCase):
    @patch('logging.basicConfig')
    @patch('logging.handlers.RotatingFileHandler')
    @patch('logging.StreamHandler')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_setup_logging_creates_dir_and_uses_rotating_handler(self, mock_exists, mock_makedirs, mock_stream, mock_rotating_file, mock_basic_config):
        mock_exists.return_value = False

        utils.setup_logging("test_logs", log_level="DEBUG")

        mock_makedirs.assert_called_with("test_logs")
        mock_rotating_file.assert_called_with(
            os.path.join("test_logs", "app.log"),
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        # Check if basicConfig was called with correct level (DEBUG=10)
        args, kwargs = mock_basic_config.call_args
        self.assertEqual(kwargs['level'], 10)

    @patch('logging.basicConfig')
    @patch('logging.handlers.RotatingFileHandler')
    @patch('logging.StreamHandler')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_setup_logging_exists(self, mock_exists, mock_makedirs, mock_stream, mock_rotating_file, mock_basic_config):
        mock_exists.return_value = True

        utils.setup_logging("test_logs")

        mock_makedirs.assert_not_called()
        mock_basic_config.assert_called()
