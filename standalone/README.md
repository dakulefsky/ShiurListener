# Shiur Player 0.9.4

An English-only local Windows x64 desktop player with a light interface, rounded controls, violet accents and a dedicated Now Playing panel. The complete portable ZIP includes Python, Tk and VLC; users install none separately. No Otzaria, pairing code, browser or network service.

Close the old player and run **shiur-player-setup-0.9.4.exe** once. Setup installs per user under `%LOCALAPPDATA%\Programs\ShiurPlayer` and creates desktop/Start menu shortcuts, without elevation, PowerShell, browser UI or separate runtime installation. Open the installed shortcut on future days.

Click **Check for updates** in the app for subsequent releases. Checks run only when requested. The app fetches a small release JSON from this repository, validates its version/URL/size/SHA-256, downloads the installer in a worker thread, saves playback state and starts setup. Setup waits for the old player process to exit before selecting and starting the new version. Program files use separate version directories and an atomic `active.json` pointer, leaving the previous version selected if extraction/activation fails. User data and audio recordings are outside the installation tree. Previous program versions are retained; old portable copies are not removed.

Update downloads are restricted to this repository's versioned raw GitHub installer URLs. TLS and SHA-256 detect transport/content mismatch; this is not code signing. A portable ZIP remains available, with the same in-app update button. Updating a portable copy installs the stable shortcut-based version with the existing standalone profile.

Every recording has its own saved position, shown in the list. **Continue listening** shows unfinished recordings in recent listening order. Switching recordings, pausing and normal closing save progress, alongside periodic checkpoints. Sudden termination can lose the newest interval; seek precision depends on the file. Keep file paths unchanged. Existing standalone 0.1.0/0.2.0/0.3.0/0.4.0 positions are reused automatically.

Hold Ctrl/Shift to select several recordings, or Ctrl+A for the visible list. Add them to a collection in one operation. Column headings sort the list by name, resume position or duration. Right-click offers playback and collection actions. The app remembers window size and sort preference. Column dividers are locked, while clicking headings still sorts. Idle refreshes preserve existing rows and slider graphics rather than recreating them.

Create and name collections yourself. Select a recording, click **Add to collection**, choose an existing collection or type a new name, then **Add recording**. Creating and assigning a new collection happens in one action. Use More to rename/delete a collection, remove a member or reset only one recording. Collections do not copy or delete audio. Bookmarks, 0.5–2× speeds, 10/15/60-second skips, sleep timer, automatic next-track playback, optional global keyboard shortcuts and floating controls are included. Minimizing automatically shows the always-on-top mini player. Restore the main window to hide an automatically opened mini player; a manually opened one stays visible. A prominent **Mini player** button also shows/hides it. Click **×** in either the expanded or collapsed mini player to hide it while audio keeps playing; use **Mini player** to reopen it. The floating window defaults to 360×150 instead of 410×224, is frameless and resizable with a 300×140 expanded minimum, and saves its size and position after dragging/resizing. Buttons rearrange with the client area. Its speed button cycles **1 → 1.5 → 2 → 0.5 → 1×** ; right-click the main speed button for individual rates. The main speed selector follows changes made in the mini player. Disable automatic showing in Settings if preferred. Close to save and stop.

See [the instructions](READ%20ME%20FIRST.txt) for keyboard shortcuts. State stays at `%LOCALAPPDATA%\ShiurPlayerStandalone\state.json`; earlier Inside/Sidekick profiles remain separate.

![Actual desktop-toolkit preview on Linux](../previews/shiur-player-modern-development.png)

## New in 0.8.0

The library uses the full window width above a permanent playback dock. Unplayed and Finished join Continue listening. Numbered recordings sort naturally, and search matches all entered words. Right-click or More offers Play next, Add to queue and Favorite; the Queue window supports reordering and removing upcoming recordings. Current audio keeps playing during queue changes.

Listening tools adds A–B section repeat, jump to time, 15/30/45/60-minute sleep presets, and pause at the end of the recording. Repeat and end-of-recording timers exclude one another. The dock displays time remaining adjusted for playback speed. The native mini player has a clickable progress strip and elapsed/remaining time.

Settings & backup exports the listening profile as JSON and restores validated backups with a pre-restore safety copy. Audio stays external and the current library folder is preserved. Seeking or skipping a remembered recording before decoder loading keeps its requested position and stays paused; completed recordings replay from the start.

## Validation

Controller and actual Tk window tests verify three separate positions, switching, reopening, near-end progress, recent ordering, filtering, batch collection assignment, sorting, window-size restoration, focused-button Space behavior, custom sliders, collections and bookmarks. Idle GUI refresh tests assert no row movement, tag rewrites or canvas reconstruction. Win32 mocks verify resize messages, saved bounds, the speed button and unchanged captions staying untouched across ten timer ticks, alongside minimize/restore behavior. The previous twice-per-second full-window erase/invalidation was removed; paints now follow content/theme/size changes. Real libVLC WAV/MP3 decode, seek, pause/resume and next-track tests pass on Linux using dummy output. Packaging verifies source bytes, preserved existing runtime, Tk library layout, x64 PE headers and the GUI subsystem. Actual Win32 mouse input and Tk controls connected to the bundled VLC runtime now pass on a Windows runner. Global shortcut registration/dispatch is tested with Win32 mocks; physical speaker output remains untested. This is an unsigned portable Windows build; Mac/Linux packages are not included.

The app has no browser control or URL-opening action. Its bundled interpreter is general purpose; this is not an OS-level browser lockdown.

## Build

```sh
DISPLAY=:99 python -m unittest discover -s standalone/tests -p 'test_*.py'
python standalone/tests/test_real_vlc.py
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w -H windowsgui' -o 'standalone/build/Shiur Player.exe' standalone/build/launcher.go
python standalone/build/package.py --base downloads/sidekick-windows-x64-1.1.0.zip --tk /path/to/extracted/tcltk
```

Window tests need a desktop display; real decoder tests need VLC and ffmpeg. Tk payload comes from the official Python 3.13.17 amd64 `tcltk.msi`, SHA256 `ae3e5f9dd998b36d14655cd3444d0af906c1849c60aee40994eeb1e460a3cabf`, extracted with msiextract. Ship `_tkinter.pyd` and its DLL dependencies, the tkinter package and Tcl/Tk script libraries, excluding IDLE, demos and tests. Source URLs and license notices are bundled.

## Installer build

Set the release in `app/version.py`, build the portable payload with `build/package.py`, then run:

```sh
python standalone/build/build_installer.py --go /path/to/go
GO111MODULE=off go test ./standalone/build/installer
```

The builder cross-compiles the stable installed launcher and self-contained setup as Windows GUI x64 binaries, embeds the full ZIP, and writes `downloads/standalone-latest.json` with size and SHA-256. Publish the new setup and channel JSON together. No store credentials or automatic publishing are involved. The installer core tests actual extraction, sequential version activation, path rejection and preservation of the separate state file. Network tests reject changed checksums, foreign origins and downgrade offers. Native Windows setup/shortcut/repair validation is recorded in the linked whole-app review.

## 0.8.0 corrections

Simpler branding, a light library and playback dock, rounded keyboard-operable controls, vector playback icons, a custom speed menu, fewer borders, unstriped rows and filename extensions hidden in the list. Mini speed defaults to 1 → 1.5 → 2 → 0.5 → 1×. Existing installations receive this corrected cycle once on upgrade; Both players use the same fixed order. Listening positions are preserved.

## 0.8.2 speed cycle
Both main and mini speed buttons use 1 → 1.5 → 2 → 0.5 → 1×, regardless of older cycle preferences. Right-click the main speed button for individual rates.

## 0.8.2 library and branding

Favorites controls are removed from the interface; existing profile metadata is retained. Rename recording in More or the right-click menu renames the actual audio file and migrates its saved position, bookmarks, collections and queue entries. The audio extension stays unchanged; conflicting or invalid names are rejected. Renaming an active recording briefly reloads it at its saved place and preserves paused/playing state.

## Tiny floating player

Click the minus button in the floating mini player to collapse it into a 144 × 44 draggable pill. Play/pause remains available; click the expand arrow to restore the previous mini-player size. Drag the empty left edge to reposition the pill. Collapsing does not pause playback. The collapsed preference and position are saved, and the expanded size is kept separately. Included in 0.9.4; native mouse controls pass on a Windows runner. User-specific display checks remain useful.

### Hover controls and individual speeds

Hover over the tiny pill to reveal backward/forward skip buttons using the configured 10/15/60-second interval. Moving away hides them again; hovering does not issue playback commands. Each recording saves its playback speed independently, including changes from the mini player, and restores it after switching recordings or restarting. Recordings without a saved speed start at 1×. The speed cycle remains 1× → 1.5× → 2× → 0.5× → 1×. Included in 0.9.4; native Windows mouse and desktop UI checks pass on a runner.

### Frameless mini-player design

The floating panel now removes the native Windows caption and frame, uses a light neutral surface with a violet transport control, draws transport/expand icons directly, and highlights secondary controls on hover. Empty panel space drags; expanded edges/corners resize. Rounded corners use Windows 11 DWM when available, with a rounded-region fallback for older Windows. Native button labels remain available for accessibility despite icon drawing. Existing custom floating themes remain supported. No additional runtime dependency is needed. Included in 0.9.4; native Windows mouse and desktop UI checks pass on a runner.

### Full-app visual refresh

The library, sidebar, search field, playback dock, queue, settings, listening tools and text-entry dialogs now share the mini-player’s violet accent and soft neutral palette. Library, search and playback areas use rounded surfaces; settings use keyboard-operable switches. Text-entry dialogs use matching controls and preserve cancellation/number validation. Existing playback, saved positions, individual recording speeds, backups and keyboard shortcuts remain in place. The main app retains standard OS window controls for minimizing, maximizing and resizing; the floating player remains frameless.

Screenshots of the running development UI with demonstration library data: [main window](../previews/shiur-player-modern-development.png), [settings](../previews/shiur-player-modern-settings.png), [listening tools](../previews/shiur-player-modern-tools.png), [queue](../previews/shiur-player-modern-queue.png). These were captured on a Linux virtual display with Tk 8.6; they are not Windows screenshots. This refresh is included in the 0.9.4 installer.

## 0.9.1 taskbar identity

The GUI sets a stable Windows AppUserModelID before creating windows, and setup writes the same identity to the desktop and Start menu shortcuts. The Tk window also loads the app’s ICO explicitly. This separates the taskbar group from the bundled Python runtime. An old taskbar pin may need to be unpinned and recreated from the updated Shiur Player shortcut. Python may still appear in Task Manager; this update changes shell branding, not the underlying runtime. Native Windows shell behavior still requires verification on Windows.

## 0.9.2 hover stability and collapsible playback panel

The main playback dock has Collapse player / Expand player controls. Its compact view keeps the title, play/pause and speed available, frees library space, and remembers the choice across restarts. Playback does not stop when collapsing.

Tiny-player hover now waits 200 ms before revealing skips and 450 ms before hiding them, ignores brief crossings and holds its layout while clicking or dragging. Hover resizing no longer rebuilds the native window frame; leaving restores the original position when expansion had to shift away from a screen edge. An explicit WM_PAINT handler clears invalidated background areas, and unchanged layouts do not repeatedly show/move controls. Automated timing, transport, painting and actual Tk collapse/restore checks pass; native Windows pointer/rendering verification remains outstanding.

## 0.9.3 mini-player click routing

Corrects WM_NCHITTEST: clickable control rectangles return HTCLIENT before resize/drag handling. Only empty surface returns HTCAPTION. The parent previously treated button areas as a draggable caption, which could stop Windows from routing pointer input to child controls. Tests now exercise the registered native window procedure’s hit targets for play/pause, skip, speed, expand, Open and seek, in addition to command notifications. Actual physical Windows mouse interaction remains unverified here.

## 0.9.4 whole-app review

Reviewed playback, recovery, state persistence, library actions, bookmarks, backups, the two interfaces, shortcuts, updating, launchers and installation. Corrected failure/retry paths, premature unmuting, stale reset seeks, loading/checkpoint races, missing-folder Refresh, invalid saved-state handling, duplicate collection names, hidden-row actions, stale bookmark windows, rename failure/aliases, update caching and same-version repair. Startup now holds a Windows instance guard to protect the shared profile from repeated launches. Native Windows tests also reproduced and corrected lost visibility on mini-player mode changes; screen-edge hover keeps play/pause anchored.

See [the detailed review and verification record](../docs/STANDALONE_REVIEW_0.9.4.md). CI runs the source tests on Linux and Windows, actual Win32 injected mouse controls, and real Windows VLC/Tk interaction using a dummy output. A manual candidate-install workflow validates the packaged EXE before the public update channel is advanced. No test-only dependencies are added to the shipped application.

