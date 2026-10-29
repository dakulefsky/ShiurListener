# Shiur Player 0.9.23

Makes the offline speech-enhancement window independently minimizable while processing continues, and reduces Python/native buffer overhead in the audio-frame conversion path. The model, settings, clipping, and output format remain unchanged; actual processing time depends on the recording and computer.

Carries forward the 0.9.22 reliability fixes for updater download startup, language preference preservation, safer profile restoration, and folder-monitor race protection. New or renamed audio files in the selected folder are detected automatically after they finish copying.

Speech enhancement remains optional and runs locally. Original recordings are never overwritten. Existing listening positions, collections, bookmarks, and original recordings are preserved.
