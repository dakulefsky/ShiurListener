# Offline sound-classification experiment

This is a developer experiment, not plugin code or an installer feature. It does not upload audio, play it, train a model, or change Inside. The separate five-minute plugin restriction remains unchanged. Benchmark clips shorter than five minutes are deliberately classified here to test content detection independently.

## Reproduce

Use Python 3.12, `ai-edge-litert==2.3.0`, NumPy, and FFmpeg on Linux. A Windows/mobile deployment has not been tested. Model, sample audio, runtime wheels and dataset archive are NOT redistributed in this repository. The downloads were used locally; do not infer redistribution rights from a public URL.

Place assets in a directory as follows:

- `yamnet.tflite`: https://storage.googleapis.com/audioset/yamnet.tflite
- `yamnet_class_map.csv`: https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv
- `dataset.zip`: https://codeload.github.com/audiocontentanalysis/dataset-gtzan-musicspeech/zip/refs/heads/main
- Extract only its `music_wav/*.wav` and `speech_wav/*.wav` to `data/music_wav/` and `data/speech_wav/`. Inspect ZIP paths before extraction.
- `shiur_freifeld.mp3`: https://rabbifreifeld.com/wp-content/uploads/2016/02/03-Strength-Of-Wisdom.1.mp3 ; published source: https://rabbifreifeld.com/recordings-2/

The model and dataset SHA-256 values and per-recording hashes are recorded in `results/baseline.json`. Upstream branch URLs can change; verify hashes when reproducing. Verify model/runtime licensing separately before any redistribution. No claim is made that this benchmark is disjoint from the model's training data.

```sh
python make_stress_samples.py --assets /path/to/assets
python evaluate_sound.py --assets /path/to/assets --output /path/to/baseline
python evaluate_sound.py --assets /path/to/assets --output /path/to/candidate --sustained-frames 3
```

Set PYTHONPATH if packages were installed into a private development directory. End users do not need to install these tools; this is not a released user-facing detector.

## Fixed initial rule

Each 15,600-sample frame (0.975 seconds) at 16 kHz mono is independently classified. A music hit is `max(Music, Singing) >= 0.5`. Block if hits cover at least 10% of actual decoded samples; otherwise allow if Speech >= 0.5 covers at least 50%; otherwise uncertain. Both block and uncertain withhold playback. These thresholds were written before the initial inference run. They are an experimental aggregation rule, not a model-provided guarantee. The entire input is decoded in chunks, with no opening-only sampling.

## Revised candidate

After the baseline missed a short music insertion in a mostly spoken file, an extra rule was tried: also block three consecutive music-hit frames (about 2.9 seconds). This rule was selected AFTER inspecting results. Its performance on these same samples is exploratory, not held-out validation. Look at both JSON reports, including the baseline failure. The `rule` text in JSON describes the initial rule; the `sustained_frames` field records the additional rule for the candidate.

## Limits

Dataset labels are inherited; not every benchmark recording was manually annotated or listened to. Only one actual shiur was successfully downloaded and tested, from one English-speaking speaker. Hebrew download attempts returned HTTP 403 and were not used. No Yiddish shiur, broad range of singing shiurim, or authentic Hebrew/Yiddish a-cappella challenge set was evaluated. Constructed challenges reuse benchmark/shiur content and are not independent recordings.

CPU timings are from a modern cloud server, not the user's Windows machine. Process peak memory includes the complete Python evaluation harness; it must not be described as the model's required memory. All results are preliminary.
