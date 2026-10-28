# Shiur Player 0.9.16

Improves the offline speech-enhancement workflow. Audio conversion now uses VLC's file-transcoding pipeline instead of normal playback callbacks, avoiding a guaranteed real-time conversion pass before denoising. Actual speed still depends on recording format, recording length, and computer performance.

Clarifies **Switch back to original**: this restores playback from the untouched source recording; the separate enhanced copy remains cached. Choosing not to switch to the enhanced copy after processing now explicitly returns playback to the original.

Modernizes right-click actions and playback-speed menus with rounded Shiur Player styling, and replaces the dialog scrollbar with a slim, rounded thumb and hover feedback.

Retains the mini-player resize fix, scrollable settings dialogs, local-only enhancement, and preservation of listening positions, collections, bookmarks, and original audio files.
