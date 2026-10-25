# Inside: offline speech/music experiment

Status: the [first offline experiment has now been run](INSIDE_SOUND_ANALYSIS_RESULTS.md); this remains a proposed production design, not an implemented plugin classifier. Inside 1.4.6 enforces duration only. The proposed host audio API is also not implemented. Preliminary measurements and their limits are recorded in the linked results report.

## What we would build first

An offline evaluation tool outside the plugin, using a pretrained audio-event model. YAMNet is one candidate to investigate, not a selected or bundled dependency. Before distribution, verify the exact model/weights license, supported runtime, model integrity and dependencies. Measure accuracy and resource use on the intended computers before choosing a browser or host runtime. There should be no dependency on Python or an external model download for end users; a successful production implementation would bundle its runtime and approved model.

Input is a user-supplied local recording. Decode it without playing, downmix/resample according to the chosen model specification, and process the whole recording in bounded-memory chunks. Model frames are aggregated into a timeline showing speech, music, overlap and uncertain regions. A speech score and a music score are not necessarily mutually exclusive probabilities; do not simply subtract one from the other. Silence is not evidence that a file is a shiur.

Inspect all content before allowing playback if the policy requires preapproval. Sampling only the beginning permits a spoken introduction to conceal later music. Scanning as playback proceeds offers weaker protection and should not be described as preapproval. Use the original recording, independently of the selected playback speed.

## Data needed

Use recordings the owner is allowed to provide. Keep them local. Include Hebrew, Yiddish and English shiurim; several speakers; noisy and low-quality recordings; pauses; sung quotations; shiurim with musical introductions; instrumental music; vocal songs; a cappella singing; music under speech; and ordinary spoken content unrelated to Torah.

Label representative timeline regions, not just whole files. Group alternate encodings, excerpts and copies of the same source recording together. Separate development/tuning and held-out evaluation sets by original recording and speaker/series where possible. Do not tune thresholds against the final held-out results.

## Policy to evaluate

1. Reject unsupported media, prohibited streams, unreadable content and files below five minutes using the host rules first.
2. Run the classifier locally over the full eligible recording.
3. Derive candidate decisions from sustained music regions and their total coverage, along with speech coverage and uncertainty. Test several thresholds; none are chosen yet.
4. Under a conservative policy, both likely music and uncertain results remain blocked. The tradeoff is more rejected shiurim. Any review/approval route must be controlled by the host/administrators, not a plugin checkbox.
5. Cache approval only against the exact content plus model version and policy version. The host must own cache decisions and ensure the checked content is the played content. A plugin-provided result is not authoritative. This is not protection against a person with unrestricted control of the computer itself.

## Report before integrating

Report how much actual music is incorrectly allowed and how many genuine shiurim are incorrectly blocked; include counts, denominators and uncertainty, not just overall accuracy. Report overlap/singing/noise cases separately. Also measure real-time processing ratio, peak memory, runtime/model download size and behavior after interruption or decode failure.

The first review deliverable should be an annotated timeline and comparison against human labels. Until those measurements exist, this should not silently block a user's library or be marketed as a music detector that cannot be bypassed.

## Decision point

If administrators accept probabilistic filtering, we can choose a model and threshold after reviewing these results and implement an offline host-side gate. If they require a guarantee of approved Torah content, use a curated catalog and an approval process instead. Speech detection alone cannot identify the subject or legitimacy of speech.
