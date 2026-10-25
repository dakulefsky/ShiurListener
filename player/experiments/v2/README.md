# Sound detector v2: experimental local scanner

This upgrades the sound-analysis prototype, not the released Inside plugin. It is not a production security gate. There is no new `.otzplugin` or end-user installer in this change.

## Changes

- Accepts a list of local recordings rather than a fixed benchmark only.
- Writes a JSON report and a self-contained HTML table with decisions, reasons and timestamps of possible music regions. The report embeds no audio, scripts or external resources.
- Conservative default: short Music/Singing candidates are held as `uncertain`, even if they occupy a tiny part of a long recording. Substantial music (10% of decoded duration) or a continuous 2.9-second music-hit stretch is blocked. Speech needs at least 50% coverage to be allowed; silence is not approval.
- Optional `--balanced` keeps the previous candidate behavior for comparison, allowing predominantly spoken material that has only brief detections. The conservative profile can reject more legitimate shiurim.
- Separates speech/music analysis from the five-minute requirement. A file is `playback_eligible` only when allowed and at least 300 seconds. All errors and uncertain outcomes withhold eligibility.
- Pins the exact tested model SHA-256 and checks class mapping, rejects non-finite scores, detects input changes during the scan, and restricts FFmpeg input protocols to file/pipe. The scanner does not open a player or alter the audio.

Checksums and file-change checks are research safeguards, not a host-owned immutable playback handle. Whole-process resource isolation, robust cancellation/time limits, parser stream validation, Windows packaging, broader content testing and host authorization remain necessary for production. Classifier policy is ordinary editable Python here; it is not tamper-proof. The installed Inside plugin remains 1.4.6 with duration filtering only.

## Run

Use the assets and development dependencies described in the [experiment guide](../README.md). No model or copyrighted recording is bundled here.

```sh
python scan.py --model /path/yamnet.tflite --classes /path/yamnet_class_map.csv --output report.json recording.mp3 another.wav
python -m unittest discover -s . -p 'test_*.py'
```

Scores are model estimates, not semantic recognition of Torah. The model is unchanged from v1; the upgrade is in decision rules, diagnostics and scanner behavior.

## New challenge results

After the rules were written, nine newly constructed music-bearing examples were made from GTZAN `geography1.wav` speech and `jazz.wav`, `opera.wav`, `rock.wav`: a two-second insertion, a five-second insertion and music underneath speech at −20 dB relative RMS for each music clip. All nine were withheld: four blocked, five uncertain. The speech-only control was allowed. These are fresh combinations of previously tested sources, not an independent held-out dataset. Short test clips deliberately test classification independently of minimum duration.

The original full Rabbi Freifeld shiur is now uncertain in conservative mode because of brief music-like detections. Its six-minute speech/15-second music challenge is blocked. This illustrates the false-rejection tradeoff rather than a claim that v2 is uniformly more accurate. Hebrew/Yiddish shiurim and authentic singing/chanting cases still need evaluation.

See `new-challenge-results.json`, `real-recording-results.json` and `new-challenge-report.html` for actual outputs. Five policy regression tests pass (short insertion, sustained music in a long recording, silence, invalid scores and actual partial-frame duration).
