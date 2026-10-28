# Shiur Player 0.9.18

Fixes offline speech enhancement conversion by bundling the VLC stream-transcoding, WAV muxing, file-output and PCM codec plugins needed for local conversion. The release pipeline now runs the real VLC conversion smoke test before publishing, so a missing runtime component blocks the release.

Audio conversion uses VLC's file-transcoding pipeline instead of normal playback callbacks, avoiding a guaranteed real-time conversion pass before denoising. Actual processing speed still depends on recording length, format, and computer performance.

Clarifies **Switch back to original**: this restores playback from the untouched source recording; the separate enhanced copy remains cached. Choosing not to switch to the enhanced copy after processing now explicitly returns playback to the original.

Modernizes right-click actions and playback-speed menus with rounded Shiur Player styling, and replaces the dialog scrollbar with a slim, rounded thumb and hover feedback. Settings remain scrollable, and the collapsed mini-player resize fix is retained.

Listening positions, collections, bookmarks, and original audio files are preserved.
