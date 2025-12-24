import unittest
import sqlite3
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from database import VideoMappingDB

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "/tmp/test_mapping.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = VideoMappingDB(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_upsert_and_get(self):
        src = Path("/source/video.mkv")
        strm = Path("/dest/video.strm")
        url = "http://example.com/video.mkv"

        self.db.upsert_mapping(src, strm, url)

        mapping = self.db.get_mapping(src)
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping['strm_path'], strm.resolve())
        self.assertEqual(mapping['seafile_url'], url)

    def test_update_mapping(self):
        src = Path("/source/video.mkv")
        strm1 = Path("/dest/video.strm")
        strm2 = Path("/dest/new_location/video.strm")

        self.db.upsert_mapping(src, strm1)
        self.db.upsert_mapping(src, strm2)

        mapping = self.db.get_mapping(src)
        self.assertEqual(mapping['strm_path'], strm2.resolve())

    def test_delete_mapping(self):
        src = Path("/source/video.mkv")
        strm = Path("/dest/video.strm")

        self.db.upsert_mapping(src, strm)
        self.db.delete_mapping(str(src.resolve()))

        mapping = self.db.get_mapping(src)
        self.assertIsNone(mapping)

    def test_get_all(self):
        mappings = {
            "/src/1.mkv": "/dst/1.strm",
            "/src/2.mkv": "/dst/2.strm"
        }
        for s, d in mappings.items():
            self.db.upsert_mapping(Path(s), Path(d))

        results = list(self.db.get_all_mappings())
        self.assertEqual(len(results), 2)
        # Convert results to dict for easier checking
        res_dict = {r[0]: r[1] for r in results}

        for s, d in mappings.items():
            self.assertEqual(res_dict[str(Path(s).resolve())], str(Path(d).resolve()))

if __name__ == '__main__':
    unittest.main()
