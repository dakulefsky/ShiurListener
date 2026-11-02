"""Tests for importing dropped audio files into the selected library folder."""
import pathlib
import tempfile
import unittest

from drop_target import copy_dropped_audio


class DropImportTests(unittest.TestCase):
    def test_copies_supported_audio_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            downloads = base / "Downloads"
            library = base / "Shiurim"
            downloads.mkdir()
            library.mkdir()
            source = downloads / "shiur.mp3"
            source.write_bytes(b"audio bytes")

            result = copy_dropped_audio([source], library)

            self.assertEqual([p.name for p in result["imported"]], ["shiur.mp3"])
            self.assertEqual((library / "shiur.mp3").read_bytes(), b"audio bytes")
            self.assertTrue(source.exists())
            self.assertFalse(result["errors"])

    def test_collision_gets_a_new_name_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            downloads = base / "Downloads"
            library = base / "Shiurim"
            downloads.mkdir()
            library.mkdir()
            (library / "shiur.mp3").write_bytes(b"existing")
            source = downloads / "shiur.mp3"
            source.write_bytes(b"new")

            result = copy_dropped_audio([source], library)

            self.assertEqual([p.name for p in result["imported"]], ["shiur (2).mp3"])
            self.assertEqual((library / "shiur.mp3").read_bytes(), b"existing")
            self.assertEqual((library / "shiur (2).mp3").read_bytes(), b"new")

    def test_ignores_unsupported_and_files_already_inside_library(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp)
            library = base / "Shiurim"
            library.mkdir()
            audio = library / "already.mp3"
            audio.write_bytes(b"audio")
            text = base / "notes.txt"
            text.write_text("not audio")

            result = copy_dropped_audio([audio, text], library)

            self.assertEqual(result["imported"], [])
            self.assertEqual(len(result["skipped"]), 2)
            self.assertEqual(list(library.iterdir()), [audio])


if __name__ == "__main__":
    unittest.main()
