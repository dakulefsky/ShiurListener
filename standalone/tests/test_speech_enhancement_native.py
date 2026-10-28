"""Native-runtime enhancement stress/measurement test.

Run on Windows after obtaining the pinned Hush assets. This is a repeatable
synthetic speech-like signal benchmark, not a substitute for listening tests on
real shiur recordings.
"""
import array
import math
import pathlib
import runpy
import statistics
import sys
import tempfile
import time
import wave


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))


def make_signal(path, seconds, seed=20261028, noise_amplitude=0.12):
    # Deterministic voiced harmonics with a syllabic envelope and low-level
    # broadband noise. It provides a known clean reference for SNR measurement.
    import random
    rng = random.Random(seed)
    rate = 16000
    clean = []
    noisy = []
    for i in range(rate * seconds):
        t = i / rate
        syllable = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(2 * math.pi * 3.1 * t)) ** 2
        f0 = 118 + 13 * math.sin(2 * math.pi * 0.7 * t)
        voiced = (0.22 * math.sin(2 * math.pi * f0 * t)
                  + 0.13 * math.sin(2 * math.pi * 2 * f0 * t)
                  + 0.08 * math.sin(2 * math.pi * 3 * f0 * t)
                  + 0.045 * math.sin(2 * math.pi * 5 * f0 * t))
        consonant = 0.025 * math.sin(2 * math.pi * (1700 + 300 * math.sin(t)) * t)
        wanted = syllable * (voiced + consonant)
        noise = noise_amplitude * rng.uniform(-1, 1)
        clean.append(wanted)
        noisy.append(max(-0.98, min(0.98, wanted + noise)))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(array.array("h", (round(x * 32767) for x in noisy)).tobytes())
    return clean, noisy


def read_float(path):
    with wave.open(str(path), "rb") as source:
        assert source.getnchannels() == 1 and source.getsampwidth() == 2 and source.getframerate() == 16000
        raw = source.readframes(source.getnframes())
        samples = array.array("h")
        samples.frombytes(raw)
        return [sample / 32768 for sample in samples], source.getnframes()


def snr_db(reference, observed):
    n = min(len(reference), len(observed))
    signal_power = sum(x*x for x in reference[:n]) / max(1, n)
    error_power = sum((reference[i] - observed[i])**2 for i in range(n)) / max(1, n)
    return 10 * math.log10(max(signal_power, 1e-15) / max(error_power, 1e-15))


def rms(values):
    return math.sqrt(sum(x*x for x in values) / max(1, len(values)))


def main():
    release = runpy.run_path(str(ROOT / "build" / "release.py"))
    assets = release["download_hush_assets"]()
    import speech_enhancement
    with tempfile.TemporaryDirectory(prefix="shiur-native-quality-") as directory:
        root = pathlib.Path(directory)
        app = root / "app"
        runtime = app / "runtime" / "speech"
        runtime.mkdir(parents=True)
        for name, data in assets.items():
            relative = pathlib.Path(name)
            if relative.parts[0:2] == ("runtime", "speech"):
                target = app / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

        source = root / "noisy-reference.wav"
        clean, noisy = make_signal(source, 12)
        source_original = source.read_bytes()
        metrics = []
        for strength in (20, 35, 50):
            output = root / f"enhanced-{strength}.wav"
            progress = []
            started = time.monotonic()
            speech_enhancement.enhance_file(
                source, output, app, strength_db=strength, progress=progress.append
            )
            elapsed = time.monotonic() - started
            processed, frames = read_float(output)
            assert frames == len(noisy), f"strength {strength}: frame count changed"
            assert source.read_bytes() == source_original, "source WAV was modified"
            assert progress and progress[-1] == 100, "progress did not finish at 100%"
            assert progress == sorted(progress), "progress moved backwards"
            clipped = sum(abs(x) >= 0.9999 for x in processed) / max(1, len(processed))
            assert clipped < 0.01, f"unexpected clipping at strength {strength}: {clipped:.2%}"
            assert rms(processed) > 0.001, f"output unexpectedly silent at strength {strength}"
            input_snr = snr_db(clean, noisy)
            output_snr = snr_db(clean, processed)
            metrics.append((strength, elapsed, input_snr, output_snr, rms(noisy), rms(processed), clipped))
            print(
                f"QUALITY strength={strength} duration=12s elapsed={elapsed:.2f}s "
                f"input_snr={input_snr:.2f}dB output_snr={output_snr:.2f}dB "
                f"input_rms={rms(noisy):.4f} output_rms={rms(processed):.4f} clipped={clipped:.4%}",
                flush=True,
            )

        # A longer file catches frame-loop, progress, and runtime scaling issues.
        long_source = root / "long-noisy.wav"
        long_clean, long_noisy = make_signal(long_source, 60, seed=20261029)
        long_output = root / "long-enhanced.wav"
        started = time.monotonic()
        speech_enhancement.enhance_file(long_source, long_output, app)
        elapsed = time.monotonic() - started
        processed, frames = read_float(long_output)
        assert frames == 16000 * 60, f"60-second output has {frames} frames"
        assert long_source.exists() and long_output.exists()
        assert elapsed < 240, f"60-second enhancement took too long: {elapsed:.1f}s"
        assert all(math.isfinite(x) for x in processed), "output contains non-finite samples"
        print(
            f"LONG duration=60s elapsed={elapsed:.2f}s realtime_factor={60/max(elapsed, 0.001):.2f}x "
            f"input_snr={snr_db(long_clean, long_noisy):.2f}dB "
            f"output_snr={snr_db(long_clean, processed):.2f}dB",
            flush=True,
        )
        print("Native enhancement stress test completed; inspect SNR results before drawing quality conclusions.", flush=True)


if __name__ == "__main__":
    main()
