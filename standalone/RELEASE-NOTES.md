# Shiur Player 0.9.22

Hardens the standalone player after a whole-app reliability audit. Fixes background updater download startup, preserves the language preference on startup and profile import, and makes profile restore safer so a failed profile write does not stop current playback.

Improves folder monitoring so a scan cannot switch the library back to an outdated folder after the user manually changes it. Normalizes natural-sort keys and adds regression coverage for these fixes.

Speech enhancement remains optional and runs locally. Existing listening positions, collections, bookmarks and original recordings are preserved.
