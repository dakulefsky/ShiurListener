# Inside sound-analysis test: actual preliminary results

Tested 25 October 2026. Conclusion: offline speech/music filtering is practical enough for a prototype, but this experiment does not establish a reliable music ban. No sound classifier was added to the released plugin.

## What actually ran

Google's YAMNet TFLite audio classifier, locally with AI Edge LiteRT 2.3.0 on a Linux Intel Xeon Platinum 8573C cloud server, two inference threads. The model is 16,061,524 bytes (15.3 MiB). All audio was decoded locally through FFmpeg at 16 kHz mono and scanned in 0.975-second frames. The experiment never played or uploaded the audio. Downloads are setup inputs; inference does not require a network service.

Inputs: 64 music and 64 speech clips from the GTZAN music/speech dataset mirror; one full 460-second Rabbi Shlomo Freifeld recording, “Strength of Wisdom”; and seven constructed challenges. Total scanned per run: 4,855 seconds, approximately 81 minutes. Short benchmark clips bypass the plugin's five-minute minimum in this experiment so the classifier itself can be evaluated.

Sources:

- [Official YAMNet implementation](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet)
- [Model used](https://storage.googleapis.com/audioset/yamnet.tflite)
- [Dataset description](https://www.tensorflow.org/datasets/catalog/gtzan_music_speech)
- [Dataset mirror used](https://github.com/audiocontentanalysis/dataset-gtzan-musicspeech)
- [Rabbi Freifeld recording page](https://rabbifreifeld.com/recordings-2/)

Model and input hashes, per-recording scores, scripts and reproduction instructions are in [player/experiments](../player/experiments/README.md). Raw recordings and model weights are not redistributed. Public availability is not a redistribution license.

## Initial rule and observed failure

Before the first run, the rule was written as: block if at least 10% of a recording has Music or Singing scores of 0.5 or more. Otherwise allow if at least 50% has Speech scores of 0.5 or more; otherwise classify as uncertain and withhold playback.

| Input | Allow | Flag music | Uncertain |
| --- | ---: | ---: | ---: |
| 64 speech clips | 64 | 0 | 0 |
| 64 music clips | 0 | 63 | 1 |
| One full Freifeld shiur | 1 | 0 | 0 |
| Seven constructed challenges | 1 | 4 | 2 |

The music clip `echoes.wav` was uncertain rather than confidently detected as music. It would still be withheld under this policy; it must not be counted as successful music identification.

The serious miss was six minutes of the Freifeld shiur followed by 15 seconds of music. The model produced music detections, but they covered only 5.36% of this file. The aggregation rule therefore allowed it. This illustrates why a percentage-only rule can miss a short song segment inside a long recording.

## Revised candidate, tested on the same material

An extra rule was added after observing that miss: also block three consecutive music-hit frames, approximately 2.9 seconds. This is a post-hoc candidate, not an independently validated threshold.

| Input | Allow | Flag music | Uncertain |
| --- | ---: | ---: | ---: |
| 64 speech clips | 64 | 0 | 0 |
| 64 music clips | 0 | 63 | 1 |
| One full Freifeld shiur | 1 | 0 | 0 |
| Seven constructed challenges | 0 | 5 | 2 |

All five constructed music-bearing files were flagged: music mixed beneath speech at relative RMS levels of −20 dB, −10 dB and 0 dB; a spoken introduction followed by music; and the six-minute speech/15-second music insertion. Silence and white noise remained uncertain and would be withheld. These are constructed challenges reusing existing input audio, not five independent real-world recordings. A legitimate shiur with background music would also be blocked under this policy.

## Practical measurements

The revised run processed the approximately 81 minutes in 22.0 seconds wall time, with 8.7 seconds spent inside model invocation. These are modern cloud-server measurements, not a prediction for the user's Windows PC. Full-harness reported peak resident memory was about 387 MiB. A separate warm-model process was observed at about 65 MiB resident; neither measurement establishes memory use of a future app integration. The model alone is 15.3 MiB; a production runtime adds size.

## What this does not establish

- Only one actual shiur, from one English-speaking speaker, was tested. Attempts to download additional Hebrew recordings returned HTTP 403; no Hebrew or Yiddish shiur was evaluated.
- Dataset labels were inherited, not manually annotated across every window. Possible overlap with the pretrained model's training material was not ruled out.
- Thresholds are exploratory. The revised rule was checked on material already seen; no independent held-out accuracy claim is justified. Zero errors among 64 examples does not establish zero real-world errors.
- Authentic a-cappella music, melodic Torah recitation, many speakers, different recording equipment, deliberate evasion and broad Hebrew/Yiddish coverage still need evaluation.
- The model recognizes audio events, not whether speech is Torah. Ordinary spoken material can pass.
- A modified plugin could remove its own classifier. Enforcement, if accepted, belongs in the host under the restrictions described in the developer specification.

## Recommendation

Proceed with an offline prototype and a fresh, labeled Hebrew/Yiddish evaluation set before adopting a blocking policy. Keep uncertain files withheld if administrators choose a conservative policy, while acknowledging that legitimate shiurim may then be rejected. Do not describe this as a guarantee against music. If approved Torah content is mandatory, use an administrator-approved catalog enforced by the host.
