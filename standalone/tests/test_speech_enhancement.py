"""Regression tests for the offline speech enhancement pipeline.

The native Hush DLL is replaced with a deterministic fake here. These tests cover
Python-side WAV framing, output integrity, cancellation and cleanup; they do not
measure real denoising quality or native-runtime performance.
"""
import array
import ctypes
import pathlib
import sys
import tempfile
import threading
import unittest
import wave
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "app"))
import speech_enhancement as enhancement
from engine import Player


class FakeFunction:
    def __init__(self, callback):
        self.callback = callback
        self.restype = None
        self.argtypes = None

    def __call__(self, *args):
        return self.callback(*args)


class FakeNativeLibrary:
    def __init__(self, frame_length=4, output_values=None):
        self.frame_length = frame_length
        self.output_values = output_values
        self.freed_sessions = []
        self.freed_models = []
        self.processed_frames = 0
        self.weya_nc_model_load_from_path = FakeFunction(lambda path: 101)
        self.weya_nc_model_free = FakeFunction(lambda model: self.freed_models.append(model))
        self.weya_nc_session_create = FakeFunction(lambda model, rate, strength: 202)
        self.weya_nc_session_free = FakeFunction(lambda session: self.freed_sessions.append(session))
        self.weya_nc_get_frame_length = FakeFunction(lambda session: self.frame_length)
        self.weya_nc_process_frame = FakeFunction(self.process_frame)

    def process_frame(self, session, incoming, outgoing):
        self.processed_frames += 1
        for index in range(self.frame_length):
            if self.output_values is not None:
                outgoing[index] = self.output_values[index % len(self.output_values)]
            else:
                outgoing[index] = incoming[index]


def write_wav(path, samples, rate=16000, channels=1, width=2):
    with wave.open(str(path), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(width)
        target.setframerate(rate)
        values = array.array("h", samples)
        if sys.byteorder != "little":
            values.byteswap()
        target.writeframes(values.tobytes())


def read_samples(path):
    with wave.open(str(path), "rb") as source:
        raw = source.readframes(source.getnframes())
        values = array.array("h")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        return source.getparams(), list(values)


class SpeechEnhancementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.source = self.root / "source.wav"
        self.output = self.root / "enhanced.wav"

    def tearDown(self):
        self.temporary.cleanup()

    def test_slow_folder_walk_does_not_hold_player_lock_or_overwrite_newer_scan(self):
        player = Player(None, self.root / "player-data", backend=object())
        first = self.root / "first-library"
        second = self.root / "second-library"
        first.mkdir()
        second.mkdir()
        (first / "old.mp3").write_bytes(b"old")
        (second / "new.mp3").write_bytes(b"new")
        entered = threading.Event()
        release = threading.Event()
        errors = []
        original_rglob = pathlib.Path.rglob

        def slow_rglob(path, pattern):
            if path.resolve() == first.resolve():
                entered.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("test did not release blocked scan")
            return original_rglob(path, pattern)

        with mock.patch.object(pathlib.Path, "rglob", new=slow_rglob):
            def scan_first():
                try:
                    player.scan(first)
                except Exception as error:
                    errors.append(error)

            worker = threading.Thread(target=scan_first)
            worker.start()
            self.assertTrue(entered.wait(timeout=2), "first scan did not reach filesystem traversal")
            acquired = player.lock.acquire(timeout=0.2)
            if acquired:
                player.lock.release()
            self.assertTrue(acquired, "filesystem traversal held the player lock")
            # A newer scan should complete while the older traversal is blocked.
            player.scan(second)
            release.set()
            worker.join(timeout=5)

        self.assertFalse(worker.is_alive(), "old scan did not finish after release")
        self.assertEqual(errors, [])
        self.assertEqual(player.root, second.resolve())
        self.assertEqual([track["name"] for track in player.tracks], ["new.mp3"])

    def test_player_default_speech_strength_matches_dialog_default(self):
        player = Player(None, self.root / "player-data", backend=object())
        self.assertEqual(player.saved["speechEnhancementStrength"], 20)

    def test_conversion_profiler_is_valid_python_source(self):
        profiler = pathlib.Path(__file__).with_name("profile_speech_conversion.py")
        source = profiler.read_text(encoding="utf-8")
        compile(source, str(profiler), "exec")

    def test_wav_validation_accepts_only_mono_16bit_16khz_pcm(self):
        write_wav(self.source, [100, -100])
        self.assertTrue(enhancement._is_supported_wav(self.source))
        other = self.root / "wrong-rate.wav"
        write_wav(other, [100, -100], rate=44100)
        self.assertFalse(enhancement._is_supported_wav(other))

    def test_process_preserves_sample_count_and_identity_audio(self):
        original = [0, 100, -200, 32767, -32768, 900, -700]
        write_wav(self.source, original)
        native = FakeNativeLibrary(frame_length=4)
        progress = []
        timings = {}
        with mock.patch.object(enhancement.ctypes, "CDLL", return_value=native):
            enhancement._process_wav(self.source, self.output, self.root / "fake.dll",
                                     self.root / "fake-model.tar.gz", None, progress.append,
                                     timings=timings)
        params, actual = read_samples(self.output)
        self.assertEqual(actual, original)
        self.assertEqual(params.nframes, len(original))
        self.assertEqual(params.framerate, 16000)
        self.assertEqual(params.nchannels, 1)
        self.assertEqual(native.processed_frames, 2)
        self.assertEqual(native.freed_sessions, [202])
        self.assertEqual(native.freed_models, [101])
        self.assertEqual(progress[-1], 98)
        self.assertGreaterEqual(timings["denoising_frame_seconds"], 0)
        self.assertGreaterEqual(timings["output_write_seconds"], 0)

    def test_output_clips_extremes_and_replaces_non_finite_values_with_silence(self):
        write_wav(self.source, [1, 2, 3, 4])
        native = FakeNativeLibrary(frame_length=4, output_values=[-1.5, 1.5, float("nan"), float("inf")])
        with mock.patch.object(enhancement.ctypes, "CDLL", return_value=native):
            enhancement._process_wav(self.source, self.output, self.root / "fake.dll",
                                     self.root / "fake-model.tar.gz", None, None)
        _, actual = read_samples(self.output)
        self.assertEqual(actual, [-32768, 32767, 0, 0])

    def test_cancelled_processing_frees_native_resources(self):
        write_wav(self.source, [10, 20, 30, 40])
        native = FakeNativeLibrary(frame_length=4)
        cancelled = threading.Event()
        cancelled.set()
        with mock.patch.object(enhancement.ctypes, "CDLL", return_value=native):
            with self.assertRaises(enhancement.EnhancementCancelled):
                enhancement._process_wav(self.source, self.output, self.root / "fake.dll",
                                         self.root / "fake-model.tar.gz", cancelled, None)
        self.assertEqual(native.freed_sessions, [202])
        self.assertEqual(native.freed_models, [101])
        self.assertEqual(native.processed_frames, 0)

    def test_invalid_native_frame_size_frees_resources(self):
        write_wav(self.source, [10, 20, 30, 40])
        native = FakeNativeLibrary(frame_length=0)
        with mock.patch.object(enhancement.ctypes, "CDLL", return_value=native):
            with self.assertRaisesRegex(RuntimeError, "unsupported frame size"):
                enhancement._process_wav(self.source, self.output, self.root / "fake.dll",
                                         self.root / "fake-model.tar.gz", None, None)
        self.assertEqual(native.freed_sessions, [202])
        self.assertEqual(native.freed_models, [101])

    def test_enhance_file_refuses_to_overwrite_original(self):
        write_wav(self.source, [1, 2, 3, 4])
        with self.assertRaisesRegex(ValueError, "separate"):
            enhancement.enhance_file(self.source, self.source, self.root)


    def test_enhance_file_defaults_to_benchmarked_strength_20(self):
        write_wav(self.source, [100, -200, 300, -400])
        runtime = self.root / "runtime" / "speech"
        runtime.mkdir(parents=True)
        (runtime / "weya_nc.dll").write_bytes(b"fake dll")
        (runtime / "advanced_dfnet16k_model_best_onnx.tar.gz").write_bytes(b"fake model")

        observed = {}

        def fake_process(source, output, library, model, cancel, progress, strength_db=20.0):
            observed["strength_db"] = strength_db
            write_wav(output, [100, -200, 300, -400])

        with mock.patch.object(enhancement, "_process_wav", side_effect=fake_process):
            enhancement.enhance_file(self.source, self.output, self.root)

        self.assertEqual(observed.get("strength_db"), 20.0)
        self.assertTrue(self.output.is_file())

    def test_missing_runtime_fails_before_touching_original(self):
        samples = [100, -200, 300]
        write_wav(self.source, samples)
        with self.assertRaisesRegex(RuntimeError, "engine is missing"):
            enhancement.enhance_file(self.source, self.output, self.root)
        _, after = read_samples(self.source)
        self.assertEqual(after, samples)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
