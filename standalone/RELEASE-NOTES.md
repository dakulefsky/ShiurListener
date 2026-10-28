# Shiur Player 0.9.14

Fixes the collapsed mini-player resize interaction: resize edges and corners take priority over nearby controls, and hover expansion is suppressed while the pointer is near a resize edge.

Fixes the Settings, Audio Enhancements and Offline Speech Enhancement windows on shorter displays. Their content is now scrollable and their initial height adapts to the screen, so lower controls remain reachable.

Allows offline speech enhancement to target a selected library recording even if playback has not started. Enhancement remains local, creates a separate copy, and never overwrites the original.

Existing listening positions, collections, bookmarks and audio files are preserved.
