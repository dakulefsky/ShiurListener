# Inside: proposed host restrictions and implemented duration rule

Inside 1.4.6 blocks recordings shorter than 300 seconds, or without a finite duration. Exactly 300 seconds is allowed. Validation happens before unmuting and before the recording becomes playable. Direct audio controls and subsequent duration changes are checked. Queue playback uses the same loader. Existing audio-only extension selection remains in place; GIF/video extensions are not offered.

This is a plugin-level duration rule. It does not identify music, and modified plugin code could remove it. Short shiurim are blocked, long songs can pass. The bundled fixed diagnostic sound is deliberately separate from imported recordings. No store approval is implied.

## Proposal for Otzaria developers (not implemented host functionality)

Keep playback in a host-owned audio engine, with no video surface or arbitrary WebView autoplay permission. Grant a specific audio-playback permission rather than broad media/background privileges. Resolve only user-authorized local file handles; do not accept arbitrary URLs or executable content. Inspect the real container and streams using a maintained media parser, rather than trusting the filename or MIME type. Reject files with video/image streams, including attached pictures if a strict no-image policy is wanted; reject animated/image formats and unsupported containers. Permit only approved audio codecs/containers. Enforce minimum duration in the host before playback, including on restored queues and every new file. Handle unknown duration by rejecting playback. A file extension rename must not bypass these checks.

Expose narrowly scoped play/pause/seek/rate/status operations. Floating controls and tab buttons should call these operations using an opaque host-owned player/session handle. They must not receive a browser-navigation, general media-rendering or script-execution capability. Scope handles to the owning plugin, revoke them on disable, recheck authorized file access and use a maintained decoder. Validate this design with altered-plugin and renamed-video tests. These measures reduce the capability exposed; they are not a promise that a decoder can never have a vulnerability.

## Speech/music classification

A waveform by itself does not establish whether content is a shiur. Offline audio classification could estimate speech/music, using repeated windows across the recording, but is probabilistic: singing, introductions, background music and silence complicate decisions; podcasts and spoken non-Torah content can also pass. A detector would need a chosen model, measured accuracy on representative Hebrew/Yiddish shiurim and music, thresholds, CPU/storage measurements and a policy for uncertain cases. No classifier has been added or evaluated in this release. It should not be represented as a reliable music ban.

If administrators require a stronger content restriction, restrict playback to a curated approved catalog or authenticated content manifest, with verification enforced by the host. That trades arbitrary personal-file import for source control. A publisher signature establishes the source/approval process, not semantic truth about the recording.

## Detailed handoff

- [Hebrew host restriction specification](INSIDE_RESTRICTIONS_FOR_DEVELOPERS.he.md)
- [Offline sound-analysis experiment plan](INSIDE_SOUND_ANALYSIS_PLAN.md)

- [Actual preliminary sound-analysis results](INSIDE_SOUND_ANALYSIS_RESULTS.md)
