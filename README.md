# Shiur Player — Standalone Windows App

An English-only local shiur player for Windows x64. The recording library and playback controls are in the desktop app. No Otzaria, plugin, account, pairing code or connection service is required.

## Download

**[Download the standalone Windows app — 0.1.0](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-windows-x64-0.1.0.zip)**

Extract the **entire ZIP**, run **Shiur Player.exe**, choose the folder containing your recordings, and press Play. Keep the runtime folders beside the executable. Python and the audio runtime are included; no separate runtime installation is needed.

After restarting the computer, open the same EXE and press Play. The chosen folder, last recording and individual listening positions are remembered. Nothing starts playing automatically. The first standalone profile is separate from the previous Inside/Sidekick profiles; those are left untouched.

## Features

- Recording list and search; user-created named collections, with no preset collections.
- Separate saved listening positions, local bookmarks and selected-recording reset.
- Play/Pause, previous/next, seeking, volume, 0.75–2× speed and 10/15/60-second skips.
- Sleep timer, automatic next recording, floating controls and opt-in Windows-wide shortcuts.
- English-only native desktop controls; no browser or WebView interface.

Minimizing keeps playback running. Closing the main window stops the app and saves progress. Run the EXE again to restore an already-running main window. Use **Rescan** after adding audio files. Recordings stay in their existing folders and are not modified, copied or deleted.

[Installation and source guide](standalone/README.md) · [Source ZIP](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-standalone-source-0.1.0.zip) · [Checksums](downloads/SHA256SUMS.txt)

## Verification and limits

Nine controller/model tests cover reopening on another day and pressing Play, fractional-second positions for multiple recordings, collections, bookmarks, resetting one recording, rescanning, search/pause, auto-next/pause, speed, skipping and timer behavior. A mocked native folder-chooser test checks selection/cancellation cleanup. A mocked Win32-window test exercises main-window Play, bookmarks, collections and close/save callbacks. Real VLC WAV/MP3 decoding and transport pass on Linux with dummy audio output.

Packaging verifies runtime/license preservation, archive/source correspondence, x64 PE structure, the Windows GUI subsystem, and absence of plugin packages or a network service. This is the first experimental standalone build. The actual native Windows interface, focus/layout/DPI and physical speaker output have not been tested on a Windows desktop here. It is not a signed installer or an automatic Windows-startup installation.

The app exposes no browser control or URL-opening command. Its bundled Python interpreter is general purpose; it is not a device-level browser/Internet lockdown tool.

## Earlier Otzaria versions

These remain available as earlier projects, but are not required by the standalone app:

- [Inside 1.4.1 plugin](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/inside-1.4.1.otzplugin) · [Inside guide](player/README.md)
- [Sidekick 1.1.0 companion ZIP](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/sidekick-windows-x64-1.1.0.zip) · [Companion guide](sidekick/README.md)
- [Hebrew Otzaria developer handoff](docs/OTZARIA_AUDIO_HANDOFF.he.md)
