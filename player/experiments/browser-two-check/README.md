# Fast browser analyzer: Inside development source 1.6.0

This brings the two-check analyzer into the plugin's browser code without Python, FFmpeg, a companion, external requests, or full-file decoding at runtime. This is development source only: no new `.otzplugin`, installer or download channel was published. Released Inside 1.5.0 remains unchanged in downloads.

## Implemented

- `player/plugin/analysis-range-audio.js` reads bounded byte ranges from Otzaria's authorized local file URL. A server that ignores Range requests is rejected; it never falls back to downloading the entire recording.
- MP3: MPEG Layer III frame parsing, ID3 skipping, Xing/Info duration and optional seek table, bounded decoder preroll for the bit reservoir, and browser decoding of a small frame fragment. If there is no frame-count header, the caller must provide the finite duration already obtained by the native audio element. MP3 seek positions remain estimates, especially without a VBR seek table.
- WAV: bounded RIFF chunk traversal, PCM 16/24/32-bit and float32, including supported WAVE_FORMAT_EXTENSIBLE subtypes; one/two channels and 8–192 kHz. Only the two PCM excerpts are read and resampled. High-rate PCM excerpts use several bounded reads rather than one oversized read.
- Development limits are 2 GiB encoded size and five minutes to eight hours duration. Unsupported formats fail rather than silently loading the whole recording. M4A, Ogg, FLAC and other formats are not implemented in this fast decoder yet.
- Exactly two 0.975-second model inputs. Positions are in the 20–35% and 65–80% regions, keyed by a hash of the bounded prefix and encoded size. Unlike the earlier native experiment, this does not read/hash the entire file. The prefix hash schedules samples; it is NOT a full-file integrity proof or approval cache key.
- Same speech-priority decision as the native experiment: both music hits block; otherwise one Speech score >=0.8 can pass, or two >=0.5 with no music hit. Remaining cases are uncertain. No extra classifier calls or follow-up scans.
- Existing bundled model/runtime, model SHA-256 verification, model reuse within the current view, cancellation, a five-second budget, and no source-approval cache. Every recording is checked again when loaded. No first-run network download is needed.
- `offline-analysis.js` is now the player adapter: it forwards metadata duration, preserves mute-before-check behavior and permits playback for provisional speech under the user's selected sampled policy. Results retain `scope: sampled_only` and `fullFileApproved: false`; that flag is not a second playback veto. This is explicitly weaker than complete-file approval.

## Actual large-file browser measurements

Chromium on the existing modern Linux development server. Tests used a second local HTTP origin for audio, CORS-exposed Range headers, CSP restrictions and an interception rule rejecting all requests outside the two local origins. No external requests occurred. JavaScript libraries were loaded before timing; the first analysis call includes model/wasm startup. These are not promises for the user's Windows computer or installed Otzaria WebView.

| Hour-long fixture | Encoded bytes | Source bytes read | Analysis time | Result |
| --- | ---: | ---: | ---: | --- |
| 192 kbps MP3 | 86,401,742 | 262,144 | 257 ms | provisional speech |
| Stereo PCM WAV | 635,040,194 | 409,520 | 40 ms | provisional speech |
| Music WAV | 115,200,078 | 127,936 | 52 ms | uncertain |

The two speech fixtures repeat the earlier Freifeld recording to an hour; the music file repeats a benchmark opera excerpt. They test size and performance, not independent new material. The old full-decode 40 MiB and decoded-sample limits have been removed from DEVELOPMENT source; the 1.5.0 download still contains the earlier implementation.

## Other real-browser tests

- VBR speech and music MP3: respectively provisional speech and music detected.
- MP3 without Xing/Info: works when supplied with host metadata duration.
- 48 kHz mono float WAV and 96 kHz stereo float WAV: pass. The 353 MB stereo float fixture needed approximately 1.56 MB of source reads, about 70 ms after model warmup.
- Integrated plugin UI test passes: source selection, speech playback after analysis, real music blocked, short-file blocking, saved positions/reload, keyboard controls, suspend/pause, bookmarks/collections and fixed sound-check behavior. All outside network requests were blocked. Actual physical audio output and an installed Otzaria remain unverified.
- 26 plugin Node tests, nine bounded-range/policy guards, and 11 native fast-analyzer regression tests passed. Guards cover ignored ranges, changed size, incorrect offsets, truncated/oversized bodies, cancellation, impossible WAV chunks, renamed GIF input, deadline checks and MPEG frame validation. Browser policy matches all 136 recorded native decisions when given those same scores.
- Official source validation: zero errors, warnings or design violations. No archive build was requested for this development version.

## 136-file browser rerun

The model was run again in Chromium with this decoder and its bounded-prefix sample schedule, rather than just replaying old native scores.

| Source group | Provisional speech | Music detected | Uncertain |
| --- | ---: | ---: | ---: |
| 64 speech clips | 64 | 0 | 0 |
| 64 music clips | 0 | 55 | 9 |
| Full Freifeld shiur | 1 | 0 | 0 |
| Five constructed mixtures | 4 | 0 | 1 |
| Silence/noise | 0 | 0 | 2 |

Median analysis time: 41 ms; maximum 305 ms in that rerun. Fixture construction, page-script loading and Python test orchestration are excluded. The same previously inspected sources were reused; short clips were repeated to five minutes. This is regression evidence, not independent accuracy validation. No Hebrew/Yiddish corpus was evaluated.

Changing the scheduling fingerprint from full-file SHA to a bounded prefix changes check locations. Results therefore should not be assumed identical on other encodings. Two tiny excerpts can miss music. The acceptance of mixtures is a deliberate user tradeoff, not a music-blocking guarantee.

## Remaining limits

This is a plugin-level heuristic, not tamper-resistant host enforcement. Checking WAV/MP3 headers and selected frames does not inspect every stream or certify that arbitrary renamed containers contain no video. Same-size file replacement without a visible validator can evade mutation checks, and replacement after analysis is not locked out. Strict media restrictions still belong in the host as described in the developer handoff.

Browser support for decoding partial MP3 fragments and authorized cross-origin Range access must be checked in installed Otzaria on each supported platform. If unsupported, the development implementation reports an error rather than bypassing checks. Whole-process resource isolation is not provided. A main-thread decode or inference call cannot be hard-interrupted at an exact deadline; checks prevent a late result from being accepted.

## Reproduce

Development tests need Playwright/Chromium and FFmpeg for preparing fixtures; the plugin itself does not require either. Use the local model/data setup documented in the original experiment. Source recordings and hour-long fixture audio are not redistributed.

```sh
node --test player/experiments/browser-two-check/test_guards.cjs
python player/experiments/browser-two-check/test_browser.py --fixtures /path/to/hour-fixtures --output large-files.json
python player/experiments/browser-two-check/evaluate_files.py --assets /path/to/inside-audio-experiment --output file-evaluation.json
```

Actual outputs are in `results/`. Source helper modules live in `player/plugin` so the browser experiment and development player exercise the same implementation.

## Deep review follow-up

[Code review and fixes](CODE_REVIEW.md) records reproduced lifecycle, seek, timeout, permission, parser and stereo issues, plus the final regression results. The current picker now advertises MP3/WAV only; existing other-format library entries are preserved. Old validation counts and benchmark files above describe the earlier integration checkpoint; review results are in `results/review/`.

## Quiet-recording improvement: bounded input preparation

Before each of the same two model calls, the input now has its constant offset removed and receives bounded gain if quiet (target RMS 0.08, maximum 16×, peak-limited when boosting). Digital silence/near-silence is not boosted. This adds no range reads, model calls, model weights, external dependencies or threshold relaxation. Results identify `preprocessing: dc-quiet-gain-v1` and record input RMS, offset and applied gain per check. This is level preparation, not general denoising or restoration of damaged speech.

Paired Chromium tests used the same encoded bytes and sample locations for baseline and candidate: 64 speech + 64 music sources, each at original level, 0.01× level (−40 dB), and 0.01× with an added 0.05 DC offset. Short sources were repeated to five minutes. Of 128 quiet speech variants, passes improved from 2 to 126; two remain uncertain/blocked. Across all 192 music variants, neither version passed any as speech. Detected music increased from 56 to 160, while the remaining music versions were uncertain and blocked. Candidate median scan time was 33.2 ms, maximum 169.6 ms on the development machine; these are not user-hardware guarantees.

The separate 136-file regression rerun retained all original counts: speech 64/64 pass; pure music 0/64 pass (55 detected, 9 uncertain); full Freifeld shiur passes; mixtures 4/5 pass; silence/noise do not pass. External requests were blocked in that rerun. These reused/synthetic examples are not an independent accuracy estimate and do not validate Hebrew/Yiddish performance.

[Paired measurements](results/preprocessing/paired-variants.json) · [Original corpus rerun](results/preprocessing/corpus-regression.json) · [Hebrew explanation](../../../docs/INSIDE_ANALYZER_IMPROVEMENTS.he.md). Reproduce the paired test with `evaluate_preprocessing.py --assets /path/to/research-fixtures --output paired.json`; it loads the baseline analyzer from Git commit `3ac22b7`, which must be present locally.
