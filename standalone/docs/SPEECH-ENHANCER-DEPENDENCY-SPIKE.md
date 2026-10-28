# Speech enhancer dependency spike — findings

## Decision gate

Do not bundle DeepFilterNet pretrained weights yet. The upstream README licenses the code MIT/Apache-2.0, but an open upstream issue asks whether that license explicitly covers released checkpoints/ONNX weights and remains unresolved. Code licensing alone is not enough to assume the model weights can be redistributed inside the installer.

Reference: https://github.com/Rikorose/DeepFilterNet/issues/712

## Candidate A: DeepFilterNet

- Pros: low-complexity full-band speech denoising; upstream documents a precompiled CLI with no Python dependency.
- Constraints: documented CLI currently accepts 48 kHz WAV only; app needs a reliable offline conversion path for the supported audio formats.
- Blocker: explicit permission/license for pretrained weights must be resolved before bundling.
- Upstream: https://github.com/Rikorose/DeepFilterNet

## Candidate B: Xiph RNNoise

- Pros: established recurrent-neural-network noise suppression; BSD-3-Clause source; small native C implementation; potential to compile into a local Windows library without a Python/PyTorch stack.
- Constraints: processing API expects mono 48 kHz PCM in short frames; app still needs a robust decoder/resampler and WAV/container handling. Quality is aimed at noise suppression, not source separation.
- License diligence: verify the exact pinned source/model artifact and all included notices and model-data terms before shipping. Prefer official Xiph sources over an unverified fork.
- Upstream: https://github.com/xiph/rnnoise

## Required next step

Build a small isolated Windows proof of concept before touching the player UI: compile the selected candidate for x64, process a controlled sample, compare the original and output by listening, record binary/model hashes and license notices, and measure processing speed and memory. Test at least one real shiur with low-level speech plus noise, and one clean recording to detect artifacts.

Do not release or claim improvement until a Windows packaged build and listening test pass. Keep originals immutable and generated output in a separate cache. If neither model can be redistributed clearly, do not bundle it; choose a model with explicit weight licensing instead.