# Standalone player review — 0.9.4

This review covers the standalone Windows player, not the Inside plugin or Sidekick. The baseline was 0.9.3. The review includes the engine, controller, full Tk interface, native floating window, global shortcuts, saved-state/backup handling, updater, launchers and installer. This is a record of findings and evidence, not a guarantee that all possible bugs have been eliminated.

## Findings corrected

| Area | Problem | Correction and regression evidence |
| --- | --- | --- |
| Loading and volume | Changing volume during loading could remove the mute used while restoring a saved place. | Save the requested volume but keep loading muted until the restore sequence completes. A failing-case regression verifies both position and final volume. |
| Loading and speed | Changing speed before a decoder was ready called its rate API unnecessarily and could fail. | Store the per-recording rate and apply it when media is ready. |
| Failed loads and timeouts | An exception or timeout could leave a pending load or active marker behind, show 0:00, or leave playback muted after a restore failure. | Clear the failed load, preserve the saved place, show the error, and make Play perform a fresh load. Tests cover start failure, timeout, seek/rate restoration failure, and retry. |
| Decoder errors | Play after a decoder error could try to resume the failed decoder without reloading the saved place. | Reload the recording on an error-state retry. |
| Reset | A previous unfinished seek could overwrite a new reset-to-zero request. | Use the same tracked-seek mechanism as normal seeking; clear repeat state. Finished/stopped recordings reload paused at zero. |
| Threading | Direct loads and background checkpoints were not consistently protected by the same lock. | Serialize player loads, snapshots, capture and persistence with the existing reentrant lock. A two-thread regression verifies that a checkpoint waits for a loading transition. |
| Repeated launches | Checking for an existing window did not cover the period before that window appeared. Two launches could share one profile. | Hold a named Windows instance handle throughout the process lifetime; a duplicate launch focuses the existing window without opening another profile. Release it even when startup fails. |
| Saved-state validation | Valid JSON with invalid field types could be accepted and rewritten before later UI failure. | Validate the bounded state file before scanning or writing. Invalid state is left untouched; there is no automatic destructive reset. |
| Disconnected library | Opening the app while the saved folder was unavailable lost the in-memory folder needed by Refresh. | Keep its path, show a reconnect message, and allow Refresh after reconnection without losing positions. |
| Collections | Duplicate names created indistinguishable choices in the assignment menu. | Reject newly created or renamed duplicate names, including differences only in letter case. Existing collections are not automatically merged or deleted. |
| Selection | Some actions fell back to the last selected recording even after filtering it out or clearing the selection. | Rename/reset/queue/assignment use the actual visible selection. Reset explicitly requires one selected row. |
| Bookmarks | A bookmark window opened for one recording could act on whichever recording was current later. | Bind its actions to the recording whose bookmarks were displayed. Tests cover switching before Jump and Delete. |
| Rename | A failed rename paused an originally playing recording. Renaming an internal file alias could rename its target instead. | Restore the previous playback intent on failure; retain lexical file paths after confinement checks so renaming an alias preserves its target. Refuse existing broken-link destinations too. |
| Backup restoration | An old pending-seek marker could survive restoration. | Clear it with the other live playback state. Existing validation, safety-backup and failure rollback checks remain in place. |
| Compact dock errors | A refresh exception could be hidden when the playback dock was collapsed. | Make the error visible in the compact dock. |
| Update checks | Release metadata could be cached; malformed metadata had inconsistent errors. | Use fresh check URLs and no-cache headers; validate object shape and reject boolean download sizes. Installer origin, size and checksum restrictions remain intact. |
| Reinstallation | Re-running the same version silently reused the existing program directory, even if damaged. | Stage and validate a complete replacement, retain the original during the swap, and restore it if replacement fails. Program repair does not touch the separate listening profile. |
| Native mode changes | Replacing the mini-player window style dropped its visible flag, making child controls disappear. | Preserve visibility across mode changes; reproduced and verified with actual Windows mouse input. |
| Screen-edge hover | Revealing controls near the right edge could move play/pause out from under the pointer. | Reveal skips to the left when necessary, preserve existing control positions, and constrain the window to the current monitor work area. A native Windows edge-hover test checks the screen coordinates and clicks play/pause. |
| Text-entry dialogs | Windows testing stalled in the modal keyboard test. | Wait for the dialog to be visible and explicitly focus its entry before waiting for completion. Windows verification is recorded below. |

The previously published mini-player fixes are also included: controls return a client hit target rather than a draggable caption; hover has entry/exit delays and does not resize during clicks/drags; the window repaints invalidated background regions. The main playback dock remains collapsible.

## Verification

- Local Linux: 98 discovered unit/Tk tests: 97 passed and the Windows-only native test skipped.
- Real Linux VLC: WAV/MP3 decode, seek, rate/volume, pause/resume, saved state, automatic next recording and sleep timer passed with a dummy audio output.
- Actual Tk controls connected to real VLC: play/pause, compact dock, switching recordings with different speeds, seeking, closing/reopening and sleep timer passed in a virtual desktop, with a dummy output.
- Installer: extraction, activation, bad-payload preservation and same-version repair tests pass. The release payload is also checked through actual extraction before publication.
- Windows: 98 tests passed in the [source validation run](https://github.com/dakulefsky/ShiurListener/actions/runs/40232916874), including actual Win32 mouse input in expanded, collapsed, hover and screen-edge modes. The Windows desktop/VLC integration test also passed using the checksum-verified published VLC runtime and a dummy output.
- Packaged installer: the [native candidate installation run](https://github.com/dakulefsky/ShiurListener/actions/runs/40232916874) passed setup and packaged-app startup, verified the installed shortcut’s AppUserModelID, exercised the actual duplicate-process guard, and reinstalled the same version while preserving a saved position and speed. The tested EXE bytes are promoted unchanged to the public update channel.

The native mouse automation waits for the complete visible control layout, rather than treating an updated mode flag as proof that resizing has finished. This prevents the test itself from clicking an intentionally not-yet-visible seek bar.

One suspected problem was not confirmed: Python safely handles `print` when its no-console process has no standard output. Shortcut registration, conflict reporting, dispatch and cleanup were tested with no console; no output-related fix is claimed.

The first Windows runs also exposed assumptions in the tests: temporary paths can use Windows short names, and a runner's screen can be smaller than a hard-coded window size. Fixtures now resolve temporary paths and use screen-fitting dimensions. These are test portability corrections, not claimed product fixes.

## Remaining limits

- A Windows runner is not the user's computer. Physical speaker output, Bluetooth/headset changes, unusual DPI or multiple-monitor arrangements, sleep/wake, pinned-taskbar icon caches and every Windows version still need representative manual checks.
- Real codec checks cover WAV and MP3 on Linux and the integration formats explicitly recorded above. This is not certification of every advertised codec/file variant.
- Seeking precision depends on the file and decoder. Saving occurs on normal actions/close plus periodic checkpoints; sudden power loss can lose the newest interval.
- Invalid saved data is preserved and reported rather than silently repaired. Existing duplicate collection names are left for the user to rename.
- The installer is unsigned. HTTPS and SHA-256 verify the expected download; they do not constitute code signing or operating-system lockdown.
- macOS/Linux product installers are not part of this Windows release.

## Useful follow-up checks on the user's Windows machine

1. Update, close/reopen, and verify separate positions and speeds for two recordings.
2. Exercise expanded mini-player controls, tiny play/pause, hover skips, drag/resize and Open; repeat near the screen edge.
3. Collapse/expand the main playback dock; minimize/restore the main window while audio plays.
4. Try the normal speaker/headset output and optional global shortcuts, checking for conflicts with other apps.
