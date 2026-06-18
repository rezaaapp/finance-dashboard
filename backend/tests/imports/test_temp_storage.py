import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.imports.utils import temp_storage


class TempStorageTestCase(unittest.TestCase):
    def test_save_temp_import_file_stays_inside_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(temp_storage, "TEMP_IMPORT_DIR", Path(temp_dir)):
                saved = temp_storage.save_temp_import_file(
                    job_id="job-1",
                    filename="../unsafe name.pdf",
                    source_file=io.BytesIO(b"%PDF-test"),
                )

                saved_path = Path(saved["path"])
                self.assertTrue(saved_path.exists())
                self.assertTrue(saved_path.is_file())
                self.assertEqual(Path(temp_dir).resolve(), saved_path.parent.resolve())

    def test_delete_temp_import_file_rejects_paths_outside_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as other_dir:
            outside_file = Path(other_dir) / "outside.pdf"
            outside_file.write_bytes(b"%PDF-outside")

            with patch.object(temp_storage, "TEMP_IMPORT_DIR", Path(temp_dir)):
                deleted = temp_storage.delete_temp_import_file(str(outside_file))

            self.assertFalse(deleted)
            self.assertTrue(outside_file.exists())

    def test_delete_temp_import_file_deletes_file_inside_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            inside_file = Path(temp_dir) / "inside.pdf"
            inside_file.write_bytes(b"%PDF-inside")

            with patch.object(temp_storage, "TEMP_IMPORT_DIR", Path(temp_dir)):
                deleted = temp_storage.delete_temp_import_file(str(inside_file))

            self.assertTrue(deleted)
            self.assertFalse(inside_file.exists())


if __name__ == "__main__":
    unittest.main()
