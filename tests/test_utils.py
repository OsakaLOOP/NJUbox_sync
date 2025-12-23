import unittest
from unittest.mock import patch, MagicMock
import shutil
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import utils

class TestUtils(unittest.TestCase):
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_thumbnail_ffmpeg_missing(self, mock_run, mock_which):
        # Simulate ffmpeg missing
        mock_which.return_value = None

        utils.generate_thumbnail('input.mkv', 'output.jpg')

        # Verify subprocess was NOT called
        mock_run.assert_not_called()

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_thumbnail_success(self, mock_run, mock_which):
        # Simulate ffmpeg present
        mock_which.return_value = '/usr/bin/ffmpeg'
        mock_run.return_value = MagicMock(returncode=0)

        utils.generate_thumbnail('input.mkv', 'output.jpg')

        # Verify subprocess called with correct args
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], '/usr/bin/ffmpeg')
        self.assertIn('-ss', cmd)
        self.assertIn('00:00:10', cmd)
        self.assertIn('output.jpg', cmd)

if __name__ == '__main__':
    unittest.main()
