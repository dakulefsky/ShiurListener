# Fixed two-check policy: file test results

The analyzer was run against 136 file fixtures without changing its rules during the test. Every successful analysis made exactly two checks (two 0.975-second windows), with no follow-up scans. No plugin was packaged or changed.

| Source group | Provisional speech | Music detected | Uncertain |
| --- | ---: | ---: | ---: |
| 64 GTZAN speech clips | 55 | 0 | 9 |
| 64 GTZAN music clips | 0 | 54 | 10 |
| One complete Rabbi Freifeld shiur | 1 | 0 | 0 |
| Five constructed speech/music examples | 3 | 1 | 1 |
| Silence and white noise | 0 | 0 | 2 |

No music-only benchmark example received provisional speech. Ten were uncertain, not positively identified as music. Fifty-five of 64 speech examples received provisional speech (85.9%); nine were withheld as uncertain (14.1%). The complete 460-second Rabbi Freifeld recording received provisional speech.

## Missed mixed examples

Three of five constructed music-bearing files received provisional speech:

- Speech with music underneath at −10 dB relative RMS.
- Speech with music underneath at −20 dB relative RMS.
- Six minutes of speech followed by 15 seconds of music.

Equal-level speech/music was detected. A spoken introduction followed by music was uncertain. Two short checks are therefore useful for fast triage of these music-only examples, but not dependable detection of music within otherwise spoken material. These results must not be summarized as “all music was blocked.”

## Timing

Per-file analysis median: 0.190 seconds; range: 0.157–0.445 seconds, on the same modern Linux cloud development machine. These times exclude model initialization and generation of the repeated fixtures. The entire evaluation, including fixture generation, took 66.2 seconds. Earlier one-hour size/performance tests are recorded separately; most files here were five-minute fixtures.

## What the files were

The original GTZAN benchmark sources are short, approximately 30-second clips. To meet the five-minute requirement, each short source was repeated to 300 seconds and converted to 16 kHz mono PCM WAV. Short constructed examples were repeated the same way. The full Freifeld recording and the six-minute-plus-music challenge were scanned directly. Repetition creates longer test files; it does not create independent new recordings or genuine full-length discourses.

Labels came from the dataset and the known construction process, not new human timeline annotations. The examples and source audio had already been used in earlier experiments, so this is a fixed-policy regression/evaluation run, not an unseen test set. It does not establish accuracy on Hebrew/Yiddish shiurim or rule out overlap with model training data.

The model, sources, runtime and download references remain those documented in the [original experiment](../README.md). Raw audio is not redistributed. `file-test-results.json` records source and fixture hashes, sample times, scores and decisions. Each result remains `full_file_approved: false`.

## Reproduce

```sh
python evaluate_files.py --assets /path/to/inside-audio-experiment --output results.json
```

Uses the existing local model and source-data directory layout, Python/NumPy/AI Edge LiteRT, FFmpeg and FFprobe. Fixtures are generated one at a time in a temporary directory and removed after evaluation. The tool does not upload or play audio.
