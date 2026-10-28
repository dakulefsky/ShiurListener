# Shiur Player 0.9.22

The Offline speech enhancement window is now a normal, independently minimizable window, so you can minimize it to the taskbar while processing continues.

Speeds up the offline enhancement pipeline by reducing Python-to-native buffer overhead for every audio frame. Audio is still processed locally, the original recording is never overwritten, and output quality/settings are unchanged. Total time still depends on recording length, file format, and computer performance.

Includes the 0.9.21 fixes for mini-player seeking/resizing, Settings text wrapping, and the Audio enhancements navigation flow. Existing listening positions, collections, bookmarks and original recordings are preserved.
