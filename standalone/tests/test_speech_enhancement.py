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

    def test_failed_processing_preserves_source_and_previous_cache(self):
        import speech_enhancement
        app = self.root / 'app'
        runtime = app / 'runtime' / 'speech'
        runtime.mkdir(parents=True)
        (runtime / 'weya_nc.dll').write_bytes(b'test runtime placeholder')
        (runtime / 'advanced_dfnet16k_model_best_onnx.tar.gz').write_bytes(b'test model placeholder')
        output = self.root / 'cached-enhanced.wav'
        output.write_bytes(b'previous valid cache')
        source_before = self.source.read_bytes()
        output_before = output.read_bytes()
        original_processor = speech_enhancement._process_wav
        def fail_processing(*args, **kwargs):
            raise RuntimeError('simulated processing failure')
        speech_enhancement._process_wav = fail_processing
        try:
            with self.assertRaisesRegex(RuntimeError, 'simulated processing failure'):
                enhance_file(self.source, output, app)
        finally:
            speech_enhancement._process_wav = original_processor
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(output.read_bytes(), output_before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
