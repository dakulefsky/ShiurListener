# Shiur Player 0.9.11

Adds optional **offline speech enhancement**. From Settings → Audio enhancements, choose **Enhance current shiur** to create a separate cleaned copy using a local CPU model. Choose a suppression strength from gentle to strong. Processing runs in the background, shows progress, can be cancelled, and works without a cloud service or runtime model download. Enhanced copies are cached separately; the original recording is never overwritten, and **Use original audio** switches back while preserving the listening position.

The enhancement can reduce hiss, hum, and some competing voices, but results depend on the recording. It is not guaranteed vocal/music separation and cannot restore speech that was not captured. Existing EQ presets remain available. The optional model/runtime and its license/dataset notices are bundled with the installer.

Includes the mini-player resizing, responsive controls, and hover-to-scrub improvements from 0.9.10. Existing listening positions, collections, bookmarks and audio files are preserved.
