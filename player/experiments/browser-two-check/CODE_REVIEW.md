# Deep code review: Inside analyzer and playback integration

Scope: development source 1.6.0, from authorized file access through metadata, two-excerpt analysis, approval, seeks, saved positions, visibility and permission recovery. No new plugin archive or download was produced. The model and two-check speech-priority decision thresholds were not changed.

## Reproduced and fixed

### Cancelled or suspended loads could become ready later

Cancellation previously reached only the active analyzer. Cancelling during file resolution or metadata loading did not invalidate the enclosing load. Suspending also did not prevent a pending analyzer result from subsequently setting `loaded=true` and unmuting the element.

Each load now has its own abort controller, checks ownership/visibility after awaits, and is invalidated by cancel/stop/suspension/page close. Late results cannot approve or clear a newer load. Metadata listeners are removed on cancellation. Already-approved recordings retain their paused ready state during suspension, so resuming does not incorrectly require a reload or start sound automatically. Intentional cancellation is not shown as an unavailable-file failure.

Evidence: controlled tests originally failed for cancellation during resolution, cancellation during metadata, and suspension during analysis. Those tests now pass. Additional tests cover Stop, a late superseded result, and approved-recording pause/resume. Real-browser UI playback/resume also passes.

### Delayed seeks could save zero instead of the resume position

The engine assigned `currentTime`, marked the file loaded and immediately captured it. If the underlying media implementation still reported its previous position while seeking, capture could replace a requested resume position of 65.432 seconds with zero.

Requested seeks now have a tracked target tied to the recording. Snapshots/checkpoints keep the requested position until the media position catches up. This also covers seek followed immediately by pause and resetting progress. The issue was reproduced with an asynchronous media-element fixture; this was not a claim that every browser exhibits delayed getters.

### The five-second check could remain pending when model startup hung

The scan's timer aborted range fetches, but `Promise.all` could still wait indefinitely for model initialization after sample reads finished. The player also waited up to 15 seconds for metadata before the analyzer budget even began.

Waits are now abort-aware. The player applies a five-second load deadline across file resolution, metadata, analysis and final permission validation. The shared model loader has its own bounded lifetime, bounded model download, exact expected byte count and checksum validation. A native decode/inference call cannot be synchronously hard-interrupted, but expired/cancelled operations cannot later grant approval.

Evidence: a never-settling model-initialization test originally hung; it now rejects when its simulated deadline fires after initialization has started. A stalled host file lookup also times out and stays muted. Monotonic elapsed-time checks prevent approval even if the JavaScript timer callback has not yet been delivered.

### Permission and duration changes were not rechecked before readiness

A file could pass initial metadata validation, then lose permission or change duration while analysis was pending; completion still marked it ready.

Permission, minimum duration and available analysis-duration consistency are now checked before unmuting. An absent/uncertain analyzer result is not approval. Runtime permission revocation invalidates readiness; the retry action can reinitialize after permission is restored and retains the saved position. Suspension before initialization avoids writing an empty checkpoint.

These are application checks, not an atomic OS/file-content lock. There remains a race between a final check and subsequent file replacement/revocation; stronger enforcement requires the host design documented separately.

### WAV metadata at a read boundary was rejected, and RIFF bounds were ignored

If a valid `fmt ` header landed at the end of the 64 KiB prefix, its payload was not fetched and a valid file was rejected. Chunk lengths were compared only with file size, so chunks could escape the declared RIFF container.

A bounded follow-up fetch now handles the crossing payload. Chunks must fit the declared RIFF extent; invalid/duplicate format metadata is rejected. Tests reproduce both cases. This does not add RF64 or every possible WAV codec.

### MP3 sniffing and metadata parsing were too permissive

The probe scanned for MPEG frame patterns after arbitrary non-audio prefixes. A constructed GIF prefix followed by valid-looking MPEG headers was accepted as MP3 metadata. It also searched a broad payload area for `Info`/`Xing`, allowing an unrelated string to be misinterpreted as a duration header.

The probe now accepts recognized bounded ID3 tag chains/zero padding before supported MPEG audio, rejects unrelated prefixes, and reads Xing/Info at the MPEG side-information position. Optional fields must fit the first frame. The placement follows the established layout used in [FFmpeg's MP3 parser](https://github.com/FFmpeg/FFmpeg/blob/master/libavformat/mp3dec.c).

The stricter prefix check initially exposed that the real Freifeld recording has two consecutive ID3 tags. A regression test and bounded multi-tag support were added before completing the review. The final full browser rerun includes that recording passing again. This is not full container validation or proof that no image/video payload exists anywhere in a file.

### Opposite-phase stereo speech became silence

Averaging left/right samples unconditionally cancelled an actual constructed stereo speech recording with opposite-phase channels. The model saw near-silence and returned uncertain.

Normal averaging is preserved, but a cancellation/one-active-channel check retains the stronger channel when averaging would destroy almost all signal. It uses the same excerpts and does not add model checks. The real Chromium fixture changed from uncertain before the fix to provisional speech afterward. Scores and source-read timings are saved in `results/review/stereo-before.json` and `stereo-after.json`.

### The file picker advertised formats the fast decoder cannot process

The development picker still offered M4A/FLAC/Ogg/etc., although the fast range decoder implements MP3 and supported WAV encodings only. New file/folder selection now advertises MP3/WAV. Existing library entries and their saved positions are retained. Unsupported/corrupt input gets a clearer Hebrew error; no silent whole-file fallback was added.

## Validation after fixes

- 59 Node tests pass across player persistence, lifecycle races, cancellation/deadline, minimum duration, format parsing, stereo handling and policy parity.
- The real Chromium player UI test passes with outside requests blocked, including revoke/regrant/retry, paused tab resume, saved positions, controls, short-file blocking and actual music blocking.
- The real Chromium 136-file corpus rerun passes with no decoding errors: 64/64 speech clips provisional speech, 0/64 music clips provisional speech (55 detected, nine uncertain), full Freifeld shiur provisional speech, constructed mixtures four provisional/one uncertain, silence/noise uncertain.
- Hour-long and format matrices still pass. On the existing development server the 86 MB MP3 was checked in about 283 ms including model initialization, and the 635 MB WAV in about 42 ms with the model warm. Exact measured timings are in `results/review/`; these are not Windows performance guarantees.
- Official Otzaria source validation: zero errors, warnings or design violations. No archive build/publishing step was requested for this review.

The source audio is the previously used research material, with short clips repeated to five minutes. These are regression results, not independent Hebrew/Yiddish accuracy validation. No recordings, model changes or new dependencies were added to this review.

## Remaining limits

Exactly two short excerpts still miss content elsewhere, and mixed speech/music is deliberately allowed in some cases. The model does not identify Torah as a subject. The selected API cannot guarantee tamper-resistant filtering against modified plugin code or same-size content replacement without reliable validators. MP3 seeking is approximate; unsupported codecs/containers remain unsupported. Actual installed Otzaria/WebView behavior on Windows/macOS/Linux and physical audio output still need device checks.
