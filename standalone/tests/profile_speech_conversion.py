"""Profile real VLC format conversion separately from native denoising on a 60-second speech clip.

This measures stages rather than claiming an optimization from elapsed time alone.
Run only on Windows after downloading the pinned Hush and VLC assets.
"""
import array
import math
import pathlib
import runpy
import sys
import tempfile
import time
import urllib.request
import wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
SAMPLE_URL = "https://raw.githubusercontent.com/pyannote/pyannote-audio/93ad8b90ca7c7c7fbf82e39e4a5a005543bda66e/src/pyannote/audio/sample/sample.wav"
SAMPLE_GIT_BLOB_SHA = "150d49a69dc2da2310fbb526759ff26638595bdc"
SAMPLE_BYTES = 960104


def install_assets(app, assets):
    for name, data in assets.items():
        target = app / pathlib.Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def process_peak_working_set_mib():
    """Return the process peak working set on Windows, including native allocations."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize / (1024 * 1024)


def main():
    import hashlib
    import speech_enhancement as se

    release = runpy.run_path(str(ROOT / "build" / "release.py"))
    assets = release["download_hush_assets"]()
    assets.update(release["download_vlc_callback_assets"]())

    with urllib.request.urlopen(SAMPLE_URL, timeout=60) as response:
        payload = response.read()
    blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
    assert len(payload) == SAMPLE_BYTES and blob == SAMPLE_GIT_BLOB_SHA, "Speech fixture checksum mismatch"

    with tempfile.TemporaryDirectory(prefix="shiur-stage-profile-", ignore_cleanup_errors=True) as directory:
        root = pathlib.Path(directory)
        app = root / "app"
        install_assets(app, assets)

        # Make a 60-second, stereo 44.1 kHz source from the pinned real-speech
        # fixture. Linear interpolation is only used to construct a format-
        # conversion workload; the quality test lives in the native test suite.
        fixture = root / "fixture.wav"
        fixture.write_bytes(payload)
        with wave.open(str(fixture), "rb") as source:
            params = source.getparams()
            raw = array.array("h")
            raw.frombytes(source.readframes(source.getnframes()))
            if sys.byteorder != "little":
                raw.byteswap()
        assert params.nchannels == 1 and params.sampwidth == 2 and params.framerate == 16000
        source_samples = [value / 32768.0 for value in raw]
        source_samples = source_samples + source_samples
        wanted_frames = 60 * 44100
        stereo = array.array("h")
        for index in range(wanted_frames):
            position = index * 16000 / 44100
            left = min(int(position), len(source_samples) - 1)
            right = min(left + 1, len(source_samples) - 1)
            fraction = position - left
            value = source_samples[left] * (1 - fraction) + source_samples[right] * fraction
            sample = max(-32768, min(32767, round(value * 22000)))
            stereo.extend((sample, sample))
        source_path = root / "source-stereo-44k.wav"
        with wave.open(str(source_path), "wb") as target:
            target.setnchannels(2)
            target.setsampwidth(2)
            target.setframerate(44100)
            target.writeframes(stereo.tobytes())

        converted = root / "converted-mono-16k.wav"
        conversion_progress = []
        pipeline_started = time.monotonic()
        peak_working_set_before = process_peak_working_set_mib()
        started = time.monotonic()
        se._convert_to_mono_16k(source_path, converted, app, None, conversion_progress.append)
        conversion_seconds = time.monotonic() - started
        with wave.open(str(converted), "rb") as wav:
            converted_params = wav.getparams()
            converted_frames = wav.getnframes()
        assert converted_params.nchannels == 1 and converted_params.sampwidth == 2 and converted_params.framerate == 16000
        assert abs(converted_frames - 60 * 16000) <= 16000, f"Converted frame count unexpected: {converted_frames}"
        assert conversion_progress and conversion_progress[-1] == 10

        enhanced = root / "enhanced.wav"
        denoise_progress = []
        stage_timings = {}
        started = time.monotonic()
        se._process_wav(
            converted, enhanced,
            app / "runtime" / "speech" / "weya_nc.dll",
            app / "runtime" / "speech" / "advanced_dfnet16k_model_best_onnx.tar.gz",
            None, denoise_progress.append, strength_db=20, timings=stage_timings,
        )
        denoise_seconds = time.monotonic() - started
        pipeline_elapsed = time.monotonic() - pipeline_started
        peak_working_set_after = process_peak_working_set_mib()
        with wave.open(str(enhanced), "rb") as wav:
            output_params = wav.getparams()
            output_frames = wav.getnframes()
            samples = array.array("h")
            samples.frombytes(wav.readframes(output_frames))
        assert output_params.nchannels == 1 and output_params.sampwidth == 2 and output_params.framerate == 16000
        assert output_frames == converted_frames, "Denoising changed the converted sample count"
        assert samples and any(samples), "Denoising output is unexpectedly silent"
        assert all(math.isfinite(x) for x in samples), "Denoising output contains non-finite samples"

        total = conversion_seconds + denoise_seconds
        duration = output_frames / 16000
        compute_seconds = stage_timings.get("denoising_frame_seconds", 0.0)
        output_write_seconds = stage_timings.get("output_write_seconds", 0.0)
        memory_report = (
            f" process_peak_working_set_mib_before={peak_working_set_before:.1f}"
            f" process_peak_working_set_mib_after={peak_working_set_after:.1f}"
            if peak_working_set_before is not None and peak_working_set_after is not None
            else " process_peak_working_set_mib=unavailable"
        )
        print(
            f"STAGE_PROFILE duration={duration:.1f}s conversion={conversion_seconds:.2f}s "
            f"denoising_wall={denoise_seconds:.2f}s denoising_frame_compute={compute_seconds:.2f}s "
            f"output_write_frames={output_write_seconds:.2f}s pipeline_elapsed={pipeline_elapsed:.2f}s "
            f"conversion_realtime={duration/max(conversion_seconds, 0.001):.2f}x "
            f"denoising_realtime={duration/max(denoise_seconds, 0.001):.2f}x "
            f"pipeline_realtime={duration/max(pipeline_elapsed, 0.001):.2f}x{memory_report}",
            flush=True,
        )
        assert conversion_seconds < 180, f"60-second VLC conversion too slow: {conversion_seconds:.1f}s"
        assert denoise_seconds < 240, f"60-second native denoising too slow: {denoise_seconds:.1f}s"


if __name__ == "__main__":
    main()
