# Analyzer development: large recordings and fast triage

Development only. No plugin, installer, download channel or installed behavior is changed in this work. Released Inside 1.5.0 still has its earlier browser implementation and limits. This experiment is a native Python/LiteRT/FFmpeg development tool, not a shipped companion or a browser integration.

## Implemented

- Up to 2 GiB per local file and eight hours duration, replacing the research scanner's need to decode a complete recording into browser memory. These are development limits, not a claim that every file up to them completes within five seconds.
- Full-file incremental SHA-256 with a 1 MiB read buffer; input audio is not loaded whole into memory.
- Audio-only stream check and at least five minutes duration.
- Twenty-four short decode windows distributed across the recording, including start and end. Interior positions are reproducible pseudorandom offsets keyed by the file hash. Re-encoding changes the hash and can change the sample positions and result.
- Concurrent local seek/decode of four windows, with bounded follow-up around at most four suspicious locations. No real-time playback is needed for analysis.
- A five-second per-file budget: checks during hashing/classification and decoder timeouts. An exceeded budget returns `incomplete`, never approval. OS reads, inference calls and process cleanup are not hard-real-time interruptible, so exact wall-clock enforcement is not guaranteed. Model startup is measured separately.
- Explicit `sampled_only` scope and `full_file_approved: false` on all outcomes. `provisional_speech` is not full-file approval. It is not wired into playback.

## Actual measurements

Modern Linux Intel Xeon Platinum 8573C cloud machine, two inference threads, four decode jobs, locally cached source files. These are not Windows-PC performance promises. Model initialization is recorded separately in the JSON.

| One-hour fixture | Encoded size | Fast-check time | Result |
| --- | ---: | ---: | --- |
| 192 kbps stereo MP3 | 86,401,742 bytes | 2.31 s | uncertain |
| 44.1 kHz stereo PCM WAV | 635,040,194 bytes | 2.68 s | provisional speech |
| 16 kHz mono music WAV | 115,200,078 bytes | 1.68 s | music detected in samples |

The complete full MP3 scan using the previous native scanner took 16.03 seconds, rather than meeting a five-second complete-scan target. It was measured in the same development session while other experimental work was running. Filesystem caches were warm; old disks and slower CPUs can take longer.

The speech fixtures repeat the previously tested 460-second Rabbi Freifeld recording to an hour; the music fixture repeats the benchmark opera clip. They test file size/duration/performance, not independent new discourses or detector accuracy. The MP3 and WAV used different hash-keyed sampling positions, so their differing decisions do not demonstrate a codec-related accuracy difference.

## Coverage tradeoff

The fast checks examined about 23–30 unique seconds out of an hour, under 1%. Reading and hashing all encoded bytes does NOT mean all audio was classified. A short song between samples can be missed. Follow-up is only triggered near sampled suspicious audio; it does not solve unsampled-region evasion.

A possible product flow is provisional fast triage plus a complete scan in the background, or cached full approval from an earlier scan. This flow is NOT implemented here and would change when sound may start, so it must be agreed with Otzaria developers. A security policy requiring complete pre-playback classification cannot claim the fast sample check is equivalent. The model and heuristic also remain imperfect after a full scan.

## Reproduce

Use the local model/runtime setup from [the original experiment guide](../README.md), Python, NumPy, AI Edge LiteRT 2.3.0, FFmpeg and FFprobe. No model/audio is redistributed in this directory.

```sh
python scan.py --model /path/yamnet.tflite --output report.json hour.mp3 hour.wav
python -m unittest discover -s . -p 'test_*.py'
```

Fixture generation (with the already-downloaded research samples):

```sh
ffmpeg -stream_loop -1 -i shiur_freifeld.mp3 -t 3600 -ac 2 -ar 44100 -c:a libmp3lame -b:a 192k hour-192k.mp3
ffmpeg -stream_loop -1 -i shiur_freifeld.mp3 -t 3600 -ac 2 -ar 44100 -c:a pcm_s16le hour-stereo.wav
ffmpeg -stream_loop -1 -i data/music_wav/opera.wav -t 3600 -ac 1 -ar 16000 -c:a pcm_s16le hour-music.wav
```

## Next integration constraint

The current plugin uses OfflineAudioContext, which decodes a whole recording. This native seek/decode prototype does not remove that browser limitation. Bringing these timings and large-file handling into Inside needs a suitable browser incremental decoder/demuxer or a host-owned bounded seek/decode API. No companion installation has been added. Host-side validation remains the correct place for restrictions that modified plugin code must not bypass.
