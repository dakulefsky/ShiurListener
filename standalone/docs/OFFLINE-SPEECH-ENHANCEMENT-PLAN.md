# Offline AI speech enhancement — implementation plan

## Goal

Make difficult shiur recordings easier to understand with optional local processing. No paid API, subscription, audio upload, telemetry, or changes to the original recording. Process one selected shiur at a time, cache the result separately, and let the user switch back to the original instantly.

## Candidate evaluation

### Hush / DeepFilterNet-SE — promising technical candidate, redistribution not yet cleared

The Hush model card states Apache-2.0 for its code and model, an 8 MB ONNX model, 16 kHz mono processing, and CPU inference. Its model is explicitly trained to reduce competing speakers as well as environmental noise. The project also provides a prebuilt Windows x64 native library, which avoids bundling PyTorch. Upstream references:
- https://github.com/pulp-vision/Hush
- https://huggingface.co/weya-ai/hush

**Open question:** Hush's own dataset manifest includes ESC-50, which is CC BY-NC 3.0, and lists other datasets with separate terms. The model card's Apache-2.0 declaration is promising but is not, by itself, proof that every training-data restriction is resolved. Do not redistribute the pretrained model in Shiur Player until that issue is clarified. Also verify that the exact Windows DLL and model files can be pinned, reproducibly obtained, and redistributed with required notices.

### DeepFilterNet native executable

Official upstream supports CPU speech denoising for 48 kHz WAV and offers a precompiled binary, but redistribution rights for its pretrained checkpoints are questioned in upstream issue https://github.com/Rikorose/DeepFilterNet/issues/712. Do not bundle the model unless the rights are clear.

### RNNoise

RNNoise is lightweight and native, but its current model-weight licensing and training-data provenance are also under active clarification in upstream issues:
- https://github.com/xiph/rnnoise/issues/286
- https://github.com/xiph/rnnoise/issues/287

Do not assume the code's BSD license automatically settles the weights' redistribution terms.

## First version behavior

- Explicit **Enhance speech** action on one selected recording, with progress and Cancel.
- Process in a worker thread so the player remains responsive.
- Store the enhanced result in an app-managed cache, outside the recordings folder.
- Never overwrite, rename, or delete source recordings.
- Make original/enhanced switching obvious; preserve normal playback if enhancement is unavailable or fails.
- No processing of the whole library in the background and no automatic model downloads.
- Keep all processing offline after installation.

## Engineering and QA requirements

1. Resolve model, code, native runtime, and training-data licensing before bundling any weights.
2. Pin exact versions and SHA-256 hashes; include third-party notices and model card.
3. Convert supported source formats through the bundled local VLC runtime into temporary mono PCM; use bounded disk space and cancellation-aware cleanup.
4. Process audio in fixed frames with a native API, then write a new cache file. Verify duration, playback, sample-rate conversion, clipping, and output integrity.
5. Cache by source identity plus model/runtime version. Clear only generated cache files when requested.
6. Measure CPU time and peak memory on an ordinary CPU-only Windows machine.
7. Test quiet/low-volume shiurim, hiss/hum, room noise, reverberation, competing voices, clipped audio, and Hebrew/Yiddish/Aramaic recordings. Real listening comparisons are mandatory; never claim a fixed accuracy percentage.

## Scope boundary

Noise suppression can reduce hiss, hum, and some background interference. Competing-speaker suppression is a harder, separate capability. Neither guarantees vocal/music source separation or restores speech that was never captured.

## Sequence

1. Resolve redistribution rights and verify a pinned Windows x64 model/runtime.
2. Build and test a small local file-processing proof of concept before UI integration.
3. Add simple Enhance / Use original controls, progress, cancellation, and cache cleanup.
4. Test the packaged installer offline on a clean Windows runner and listen to real samples before publishing.
