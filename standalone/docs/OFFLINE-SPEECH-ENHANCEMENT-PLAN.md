# Offline speech enhancement plan

Goal: optional local speech denoising for Shiur Player. No paid API, upload, subscription, or source-file modification.

Evaluate the official DeepFilterNet native executable first. Upstream documents a precompiled binary without Python dependencies, operating on 48 kHz WAV. Verify Windows x64 availability, exact hashes, model and code licenses, and offline behavior before bundling.

First version should be explicit and opt-in: process a selected recording in the background, show progress/cancel, cache output outside the recordings folder, preserve original playback, and allow returning to the original. No runtime model download.

Scope: denoising can reduce hiss, hum, and some background noise. It does not reliably separate simultaneous speakers or guarantee vocal/music separation. Do not claim a fixed accuracy rate.

Before release: validate CPU speed/memory; test Hebrew/Yiddish/Aramaic speech plus quiet, noisy, reverberant and clipped recordings; verify duration/sample rate, cancellation, disk-space errors, corrupt inputs, cache cleanup, Windows packaging and offline operation. Require real listening tests as well as CI.

Sequence: (1) verify dependency, provenance, licensing and Windows runtime; (2) build isolated conversion/enhancement/cache adapter; (3) add simple Enhance/Use original UI; (4) package and test end-to-end. Keep normal playback and the existing EQ working if enhancement is unavailable or fails.