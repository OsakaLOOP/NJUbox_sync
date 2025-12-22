import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from rclone_wrapper import RcloneWrapper

class TestRcloneWrapper(unittest.TestCase):
    @patch('subprocess.run')
    def test_upload_success(self, mock_run):
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = RcloneWrapper("MyRemote", "10M")

        # Test
        result = wrapper.upload("/path/to/file", "/remote/dir")

        # Assert
        self.assertTrue(result)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "rclone")
        self.assertEqual(args[1], "copy")
        self.assertIn("/path/to/file", args)
        self.assertIn("MyRemote:/remote/dir", args)
        self.assertIn("--bwlimit", args)
        self.assertIn("10M", args)

    @patch('subprocess.run')
    def test_upload_failure(self, mock_run):
        # Setup mock
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Some error"
        mock_run.return_value = mock_result

        wrapper = RcloneWrapper("MyRemote")

        # Test
        result = wrapper.upload("/path/to/file", "/remote/dir")

        # Assert
        self.assertFalse(result)
