# נגן שיעורים / Shiur Player — companion 1.1.0

We use **Sidekick** as the conversational nickname. Its displayed name is **נגן שיעורים** in Hebrew and **Shiur Player** in English. It remains separate from Inside and keeps the same companion plugin ID and saved-data directory.

## Install or update

1. Close any older command-prompt companion first.
2. Extract the entire ZIP into a new folder and run **Sidekick.exe**. The executable and Python launcher now use the Windows GUI subsystem, with no console window.
3. In the normal setup window, choose **English** or **עברית**, then click **Choose recordings folder / בחירת תיקיית שיעורים**. Select the folder containing your audio files. The window shows its full path and recording count.
4. Click **Copy code**. Install **sidekick-1.1.0.otzplugin** from the same ZIP in Otzaria as an update. Restart Otzaria once, then open **נגן שיעורים**, paste the code and click **Connect / חיבור**.
5. Click a recording or press Play. If recordings exist but none is selected, Play chooses the first. The plugin disables playback controls for an empty library and offers folder-selection instructions.

The plugin also has **Choose recordings folder**, **Rescan folder**, and **Open desktop app** controls. Choosing a folder opens the desktop app's native picker. Rescan actually reads the disk, so newly added recordings appear without restarting. The selected folder is remembered; no folders are pre-created. Recordings are never copied, modified or deleted.

## Hide, reopen and exit

Closing the setup window with X hides it without stopping playback. **Hide and keep listening** does the same. Run the EXE again to reopen the existing window, use **Open desktop app** in the plugin, or use **Library / connection** on the floating bar. **Exit player** in the setup window stops the app and saves progress. The small floating bar can be hidden independently.

Updating preserves `%LOCALAPPDATA%\ShiurPlayerCompanion\state.json` and existing plugin storage. Do not uninstall or clear data first. Older releases did not remember the source folder, so choose it once after this update. Remembered pairing remains optional, and the code changes when the native app restarts.

## What caused the reported problems

The old companion scanned audio only at startup, while its Refresh button only fetched that old list. A file added later therefore remained absent. It also exposed playback actions before a recording had been selected, resulting in a misleading “Select a recording first” error. The console was the old application's lifetime owner, so closing it killed playback.

This version separates setup from playback, owns its lifecycle in a normal native window, rescans on request, shows folder/count information, and guards empty-library controls. A source-path change or missing file does not erase per-recording saved positions or organizational collection membership.

## Language

Both the setup window and the Otzaria controller offer Hebrew and English. The controller switches text direction between RTL and LTR and remembers the selection. The native floating bar follows the selected language. Recording names, source paths, user-created collections and bookmarks are preserved as user text. The OS folder-picker buttons follow Windows' own UI language.

## Verification and limits

Ten backend/browser tests cover pairing, folder rescans, empty/first launch, folder restoration, saved positions, language switching/persistence, playback commands, bookmarks, keyboard controls, sleep timer and queue advancement while the plugin is hidden. English controls are checked with the advanced panels open and after periodic status refresh.

One mocked native-window test checks hide/reopen, clipboard copy, language, rescan and exit callbacks. Two floating-bar and two shortcut tests pass using mocked Windows APIs. Real VLC WAV/MP3 decoding, seeking, saved positions, pause/resume and background advancement pass on Linux using a dummy audio output. The real Otzaria packager validates the plugin's manifest and design. Archive validation checks source correspondence, runtime/license preservation, x64 PE structure, and Windows GUI subsystem (2) for the launcher.

The native Windows application has not been executed on a Windows desktop here. Actual window rendering/focus, the PowerShell folder picker, and physical speaker output still need real-device checking. No new macOS/Linux executable is provided; source CLI use requires `--folder` and installed Python/VLC.

No separate Python or VLC installation is needed for the portable Windows ZIP. The service stays authenticated on `127.0.0.1:18473`, accepts no arbitrary disk path through its HTTP commands, and exposes no browser or URL-opening API. Folder access comes from the user's native picker. Bundled Python remains a general interpreter; this is not a device lockdown tool.

## Develop

```sh
python tests/test_companion.py
python tests/test_desktop.py
python tests/test_floating_bar.py
python tests/test_hotkeys.py
```

The browser test needs Playwright and Chromium. The optional `test_real_vlc.py` needs VLC 3 and ffmpeg and uses a dummy audio sink. From a Flutter/Otzaria checkout, run the packaging test with `SIDEKICK_ROOT` pointing to this directory.

Compile the GUI launcher with Go:

```sh
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w -H windowsgui' -o 'build/windows/Sidekick.exe' build/windows/launcher.go
python build/package_sidekick.py --base /path/to/shiur-player-companion-windows-x64.zip
```

The base ZIP supplies the existing licensed runtime. `desktop.py` is included explicitly in the new bundle; isolated Python loads it by absolute module path. Upstream license/source notices are preserved.

After successful pairing, the plugin code form and native setup window hide automatically. Connection settings and Open desktop app reopen them. Audio continues.
