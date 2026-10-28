# Shiur Player 0.9.14

Fixes the collapsed mini-player resize interaction. Resize edges and corners take priority over nearby controls, and hover expansion is suppressed while the pointer is near a resize edge so the pill does not move away while you try to make it smaller.

Fixes custom button callback updates used by the offline speech-enhancement dialog. The Enhance, Use enhanced copy, Use original audio, Cancel and Done controls can now receive their intended actions. Settings and Audio enhancements windows are larger and resizable, and the keyboard-shortcut instructions wrap instead of clipping off the right side.

Includes the prior 0.9.12 offline speech-enhancement feature. Processing runs locally, caches a separate enhanced copy, and never overwrites the original recording. Results vary by recording; this is not guaranteed vocal/music separation.

Existing listening positions, collections, bookmarks and audio files are preserved.
