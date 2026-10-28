"""Native speech-enhancement quality and long-file performance checks.

Uses a checksum-pinned, public-domain human speech sample plus known added noise
for an objective SNR comparison. A deterministic synthetic signal separately
stresses long-file processing. Listening tests on actual shiur recordings remain
necessary before making broad real-world quality claims.
"""
import array
import hashlib
import math
import pathlib
import random
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


def read_float(path):
    with wave.open(str(path), "rb") as source:
        params = source.getparams()
        raw = source.readframes(source.getnframes())
        samples = array.array("h")
        samples.frombytes(raw)
        return [sample / 32768 for sample in samples], params


def write_float(path, samples, rate=16000):
    values = array.array("h", (round(max(-0.999, min(0.999, x)) * 32767) for x in samples))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(values.tobytes())


def make_real_noisy_sample(root):
    with urllib.request.urlopen(SAMPLE_URL, timeout=60) as response:
        payload = response.read()
    blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
    assert len(payload) == SAMPLE_BYTES and blob == SAMPLE_GIT_BLOB_SHA, (
        f"Public-domain speech fixture changed: bytes={len(payload)}, git_blob={blob}"
    )
    clean_file = root / "human-speech-clean.wav"
    clean_file.write_bytes(payload)
    clean, params = read_float(clean_file)
    assert params.nchannels == 1 and params.sampwidth == 2 and params.framerate == 16000, (
        f"Expected mono 16-bit 16 kHz fixture; got {params}"
    )
    count = min(12 * 16000, len(clean))
    clean = clean[:count]
    base_rms = math.sqrt(sum(x*x for x in clean) / max(1, count))
    assert base_rms > 0.005, "Speech fixture unexpectedly silent"
    gain = min(0.75 / max(abs(x) for x in clean), 0.16 / base_rms)
    clean = [x * gain for x in clean]
    rng = random.Random(20261028)
    noisy = [max(-0.98, min(0.98, x + rng.gauss(0, 0.045))) for x in clean]
    clean_path = root / "reference.wav"
    noisy_path = root / "noisy-human-speech.wav"
    write_float(clean_path, clean)
    write_float(noisy_path, noisy)
    return clean_path, noisy_path, clean, noisy


def make_synthetic_signal(path, seconds, seed=20261029, noise_amplitude=0.12):
    rng = random.Random(seed)
    clean, noisy = [], []
    for i in range(16000 * seconds):
        t = i / 16000
        syllable = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(2 * math.pi * 3.1 * t)) ** 2
        f0 = 118 + 13 * math.sin(2 * math.pi * 0.7 * t)
        voiced = (0.22 * math.sin(2 * math.pi * f0 * t)
                  + 0.13 * math.sin(2 * math.pi * 2 * f0 * t)
                  + 0.08 * math.sin(2 * math.pi * 3 * f0 * t)
                  + 0.045 * math.sin(2 * math.pi * 5 * f0 * t))
        consonant = 0.025 * math.sin(2 * math.pi * (1700 + 300 * math.sin(t)) * t)
        wanted = syllable * (voiced + consonant)
        clean.append(wanted)
        noisy.append(max(-0.98, min(0.98, wanted + noise_amplitude * rng.uniform(-1, 1))))
    write_float(path, noisy)
    return clean, noisy


def snr_db(reference, observed):
    n = min(len(reference), len(observed))
    signal_power = sum(x*x for x in reference[:n]) / max(1, n)
    error_power = sum((reference[i] - observed[i])**2 for i in range(n)) / max(1, n)
    return 10 * math.log10(max(signal_power, 1e-15) / max(error_power, 1e-15))


def rms(values):
    return math.sqrt(sum(x*x for x in values) / max(1, len(values)))


def align_for_diagnostic(reference, observed, max_lag=5120, stride=16):
    """Estimate coarse global delay so a buffering offset is not mistaken for noise."""
    ref = reference[::stride]
    obs = observed[::stride]
    radius = max_lag // stride
    best_lag, best_score = 0, float("-inf")
    for lag in range(-radius, radius + 1):
        if lag < 0:
            left, right = ref[-lag:], obs[:len(obs) + lag]
        elif lag > 0:
            left, right = ref[:-lag], obs[lag:]
        else:
            left, right = ref, obs
        n = min(len(left), len(right))
        if n < len(ref) // 2:
            continue
        score = sum(left[i] * right[i] for i in range(n))
        if score > best_score:
            best_lag, best_score = lag, score
    lag_samples = best_lag * stride
    if lag_samples < 0:
        return reference[-lag_samples:], observed[:len(observed) + lag_samples], lag_samples
    if lag_samples > 0:
        return reference[:-lag_samples], observed[lag_samples:], lag_samples
    n = min(len(reference), len(observed))
    return reference[:n], observed[:n], 0


def main():
    release = runpy.run_path(str(ROOT / "build" / "release.py"))
    assets = release["download_hush_assets"]()
    import speech_enhancement
    # Windows locks the native DLL until process exit; ignore cleanup errors for
    # this disposable test runtime only.
    with tempfile.TemporaryDirectory(prefix="shiur-native-quality-", ignore_cleanup_errors=True) as directory:
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

        _, source, clean, noisy = make_real_noisy_sample(root)
        source_original = source.read_bytes()
        input_snr = snr_db(clean, noisy)
        output_snrs = []
        for strength in (20, 35, 50):
            output = root / f"human-enhanced-{strength}.wav"
            progress = []
            started = time.monotonic()
            speech_enhancement.enhance_file(
                source, output, app, strength_db=strength, progress=progress.append
            )
            elapsed = time.monotonic() - started
            processed, params = read_float(output)
            assert params.nchannels == 1 and params.sampwidth == 2 and params.framerate == 16000
            assert len(processed) == len(clean), f"strength {strength}: frame count changed"
            assert source.read_bytes() == source_original, "source recording was modified"
            assert progress and progress[-1] == 100, "progress did not finish at 100%"
            assert progress == sorted(progress), "progress moved backwards"
            assert all(math.isfinite(x) for x in processed), "output contains non-finite samples"
            clipped = sum(abs(x) >= 0.9999 for x in processed) / max(1, len(processed))
            assert clipped < 0.01, f"unexpected clipping at strength {strength}: {clipped:.2%}"
            assert rms(processed) > 0.001, f"output unexpectedly silent at strength {strength}"
            output_snr = snr_db(clean, processed)
            aligned_clean, aligned_processed, lag = align_for_diagnostic(clean, processed)
            if lag < 0:
                aligned_noisy = noisy[-lag:]
            elif lag > 0:
                aligned_noisy = noisy[:-lag]
            else:
                aligned_noisy = noisy
            aligned_input_snr = snr_db(aligned_clean, aligned_noisy)
            aligned_output_snr = snr_db(aligned_clean, aligned_processed)
            output_snrs.append(aligned_output_snr)
            print(
                f"REAL_SPEECH strength={strength} duration=12s elapsed={elapsed:.2f}s "
                f"input_snr={input_snr:.2f}dB raw_output_snr={output_snr:.2f}dB "
                f"aligned_input_snr={aligned_input_snr:.2f}dB aligned_output_snr={aligned_output_snr:.2f}dB "
                f"estimated_lag={lag}samples "
                f"input_rms={rms(noisy):.4f} output_rms={rms(processed):.4f} clipped={clipped:.4%}",
                flush=True,
            )
        best_gain = max(output_snrs) - aligned_input_snr
        print(f"REAL_SPEECH best_aligned_snr_gain={best_gain:.2f}dB across tested strengths", flush=True)
        assert best_gain >= 0.5, (
            f"Speech enhancement did not improve delay-aligned objective SNR on the pinned human-speech fixture "
            f"by at least 0.5 dB (best gain {best_gain:.2f} dB)."
        )

        long_source = root / "long-synthetic.wav"
        long_clean, long_noisy = make_synthetic_signal(long_source, 60)
        long_output = root / "long-enhanced.wav"
        started = time.monotonic()
        speech_enhancement.enhance_file(long_source, long_output, app)
        elapsed = time.monotonic() - started
        processed, params = read_float(long_output)
        assert params.nframes == 16000 * 60, f"60-second output has {params.nframes} frames"
        assert elapsed < 240, f"60-second enhancement took too long: {elapsed:.1f}s"
        assert all(math.isfinite(x) for x in processed), "long output contains non-finite samples"
        print(
            f"LONG duration=60s elapsed={elapsed:.2f}s realtime_factor={60/max(elapsed, 0.001):.2f}x "
            f"input_snr={snr_db(long_clean, long_noisy):.2f}dB "
            f"output_snr={snr_db(long_clean, processed):.2f}dB",
            flush=True,
        )
        print("Native enhancement quality and long-file benchmark completed.", flush=True)


if __name__ == "__main__":
    main()
