# Shiur Player — standalone 0.1.0

A native Windows x64 desktop player. All library and playback controls live in the app. It does not require Otzaria, a plugin, an account, a browser, an HTTP service or a pairing code. The portable ZIP includes Python and the reduced VLC runtime; end users install neither separately.

## Everyday use

Extract the complete ZIP, run **Shiur Player.exe**, choose your audio folder once, and press Play. After a computer restart, open the same EXE and press Play again. The app remembers the folder, selected recording, positions, speed, volume, collections and bookmarks. It never starts sound automatically.

Recordings stay in place. Use **Rescan** after adding files. A separate per-recording position is written on pause, change and normal shutdown, plus periodic checkpoints. Forced termination or power loss can lose the most recent interval; actual seek precision depends on the decoder.

The native main window includes search, All/Continue/custom collection views, Play/Pause, previous/next, seek, volume, speed 0.75–2×, 10/15/60-second skips, auto-next, sleep timer, bookmarks and individual position reset. Collections start empty and are created/named by the user. Removing a collection does not remove audio files. Use the collection-name field with New/Rename; select a target collection and Add to assign a recording.

The interface is English only. User-created names and recording names are preserved. The standard Windows folder-picker buttons follow the OS language.

Minimize the player to keep listening. X closes the app and saves/stops playback. The floating-player button shows/hides independent always-on-top controls; their Open player button restores the main window. Running the EXE a second time restores the existing main window rather than starting a second instance.

Ctrl+Space and Ctrl+Left/Right work inside the app. The opt-in **Shortcuts in other apps** checkbox registers the Windows-wide Ctrl+Alt+Shift shortcuts. No keyboard hook captures typing. Conflicts are reported; settings can be edited in the profile's hotkeys.json after first enabling them.

## Data and packaging

The profile is `%LOCALAPPDATA%\ShiurPlayerStandalone`. Old Inside and Sidekick profiles are left alone; there is no automatic migration in this first build. Close old players to avoid double playback or shortcut conflicts. It does not add itself to Windows startup. A normal desktop shortcut can target the portable EXE.

`app/main.py` owns lifecycle and starts a local playback worker, native main window, floating bar and optional global shortcuts. `engine.py` is the local audio/persistence model reused from the companion, with its server and pairing code removed. `controller.py` handles collections/bookmarks and selection. `window.py` is the native desktop interface. No WebView is used.

## Verification and limits

Nine model/controller tests verify the next-day reopen-and-play flow, separate fractional-second positions, local bookmarks, custom collections, reset, rescanning/confinement, search/pause, speed, skipping and timer. One native-window callback test exercises Play, bookmarks, collection assignment and close/save through mocked Windows APIs. Real libVLC WAV/MP3 transport, seek, pause/resume, persistence and automatic next-track decoding pass on Linux with dummy audio output.

Packaging verifies archive integrity, source correspondence, preserved runtime/license bytes, x64 PE headers, Windows GUI subsystem, and absence of plugin packages or a connection service. The actual Windows application has not been run on a Windows desktop here. Native rendering, DPI/layout, focus behavior, global shortcuts and physical speaker output still require Windows validation. This is a first experimental build, not a signed installer. No Mac/Linux desktop build is included.

The app has no browser control, URL-opening command or network service. Python is bundled as a general interpreter; this is not a device-level Internet/browser lockdown mechanism.

## Develop

```sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/test_real_vlc.py
```

The optional real-decoder check needs VLC 3 and ffmpeg and uses a dummy audio sink. Go builds the GUI launcher, and Python packages the existing licensed runtime:

```sh
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w -H windowsgui' -o 'build/Shiur Player.exe' build/launcher.go
python build/package.py --base /path/to/sidekick-windows-x64-1.1.0.zip
```

Licenses and runtime source URLs are preserved from the base runtime ZIP. The installed user needs only the complete extracted bundle.

The folder chooser uses Windows shell APIs directly, without PowerShell. Its selection/cancellation and COM-resource cleanup are covered with native API mocks.
