import pathlib
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
from speech_enhancement import enhance_file, _is_supported_wav


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.source = self.root / 'source.wav'
        with wave.open(str(self.source), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\x00\x00' * 1600)

    def tearDown(self):
        self.temp.cleanup()

    def test_detects_expected_wav_format(self):
        self.assertTrue(_is_supported_wav(self.source))
        stereo = self.root / 'stereo.wav'
        with wave.open(str(stereo), 'wb') as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b'\x00\x00' * 3200)
        self.assertFalse(_is_supported_wav(stereo))

    def test_never_allows_source_to_be_the_output(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'separate from the original'):
            enhance_file(self.source, self.source, self.root, progress=None)
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_runtime_fails_without_touching_source(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'speech engine is missing'):
            enhance_file(self.source, self.root / 'enhanced.wav', self.root)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse((self.root / 'enhanced.wav').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
