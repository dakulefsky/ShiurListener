# Inside 1.4.1

A Hebrew Otzaria player for local shiurim, with a simpler layout, separate saved listening positions and recovery controls. Install the plugin directly; no companion, Python or VLC installation is needed.


## Recognizing the correct player

The heading must say **Inside 1.4.1**, including in compact mode. The Hebrew error “מנוע הדפדפן של אוצריא חסם שמע ללא לחיצה במופע הרקע. בגרסה זו נדרש שינוי מדיניות באוצריא.” was found in the old 1.2 background player's `background.js`; it is absent from the visible-page player. Seeing it means that older UI/code is running.

Install this package as an update, fully quit Otzaria (including its tray instance if it remains running), reopen it and open **Inside** from the plugin list. Do not uninstall or clear data. If the heading does not say Inside 1.4.1, the new page is not running yet. This patch makes the version unmistakable; the audio engine is the same visible-page engine as 1.4.0.

## Install and listen

1. Download `inside-1.4.1.otzplugin` and install it in Otzaria as an update. Do not uninstall the existing plugin or clear its data first.
2. Restart Otzaria once and allow the plugin to read user-selected files. Otzaria 0.9.98 or newer is required.
3. Click **הוספת שיעור** to choose one recording, or **ייבוא תיקייה** to import a recordings folder. The first new recording loads silently.
4. Wait for **מוכן לניגון**, then press the large **ניגון** button. Selecting another recording loads it; press Play to begin sound.
5. Create named organizational folders with **תיקייה חדשה**. Each recording's **אפשרויות** menu contains folder assignment, reset and removal. These operations do not modify the original audio files.

Play, skip, speed, volume and saved position are together at the top. Timer, automatic next-track playback and bookmarks are under a disclosure. **נגן קטן** reduces the interface for a narrow pane.

## If it does not play

- The player now shows the failure and offers **ניסיון נוסף**. Grant missing file permission in Otzaria's plugin settings, reconnect a missing drive or select an available recording, then retry.
- Open **עזרה**, then click **השמעת צליל בדיקה**. This bundled sound needs no recording from your library. It pauses the current shiur. If the sound is not audible, check Otzaria's volume/output device. Successful browser playback alone cannot verify that sound reaches the speakers.
- If the test sound is audible but the recording is not, try a known MP3 or WAV. The same help panel includes a direct native audio strip for the selected recording.
- Expand **פרטי התקלה** to copy the version and error message. Send those details with the Otzaria version when reporting a remaining problem.

An invalid old playback queue no longer blocks valid recordings. A missing last-used recording no longer leaves Play targeting an unloaded file. Permission/initialization failures can be retried; closing the page after a failed library read does not overwrite the library with an empty one. Older WebViews without `crypto.randomUUID` get local-ID compatibility. These recovery fixes are retained from 1.4.0. The subsequently supplied background-policy error was traced to the old 1.2 background build, as described above.

## Read while listening

Open a book and the player. Right-click the player's tab, choose **הצג לצד**, then choose the book. Keep the player pane visible. **נגן קטן** hides the library to leave compact controls. This route is supported by the inspected Otzaria source, but has not been exercised in an actual Otzaria desktop installation here.

Switching to a top-level tab that hides the player, closing its pane or minimizing Otzaria may pause sound. True hidden-tab playback, a floating desktop bar and global shortcuts require host support. The [Hebrew developer handoff](https://github.com/dakulefsky/ShiurListener/blob/main/docs/OTZARIA_AUDIO_HANDOFF.he.md) explains the changes. Proposed APIs in that document are not called by this plugin.

## Stored positions and controls

The plugin retains ID `org.shiurplayer.local` and the `library-v1` / `shiur-audio-v1:*` storage keys, so updating preserves existing data. Every shiur has its own millisecond checkpoint. Pause, seek and track changes save progress; playback checkpoints about twice per second. A sudden crash can still lose the most recent unsaved interval, and actual seek precision depends on the audio decoder.

Skip intervals: 10/15/60 seconds. Speeds: 0.75–2×. Space toggles playback, arrows skip, 1/2/3 choose the interval, +/- changes speed, Shift+arrows selects a recording, B bookmarks, F searches, N creates a folder. Typing in fields is not intercepted. Tab and Enter operate the controls. Bookmarks are under the advanced disclosure.

Network access is disabled. There is no browser-opening permission, address field or external link in the player. These choices are not a device-wide browser lockdown.

## Verification and source development

- Eight persistence regressions cover checkpoint preservation, malformed queues, stale state, migration, individual reset, write failure and recent listening.
- Real-WAV Chromium tests enforce `document-user-activation-required`, check that Play is called from a real click and cover playback, pause, seek, two-track resume, reload, compact layout, speed, keyboard, auto-next, timer, folders, sound check and missing-file retry.
- The host-bridge test uses the actual Otzaria SDK stub/boot JavaScript from the inspected checkout, a `file://` plugin page, matching CSP sources and a separate loopback media origin. It covers permission retry, failed-library-read preservation, UUID compatibility, saved milliseconds, failed-file retry and actual SDK lifecycle events.
- An additional integration harness serves a real WAV through Otzaria’s actual Dart `PluginFileServer`, including its generic MIME type, no-sniff and Range headers; playback/resume passed. This does not reproduce a native Windows WebView2 installation.
- Otzaria's real packager validates the manifest, permissions and design.

These are browser and packaging checks. The build has not been tested in an installed Windows/macOS/Linux Otzaria application, and physical speaker output is unverified.

The following are developer tools only; installed-plugin users do not need them:

```sh
node --test tests/test_resume.cjs
python tests/test_direct_player.py
OTZARIA_SOURCE_ROOT=/path/to/otzaria python tests/test_host_bridge.py
```

Browser tests need Python Playwright and Chromium. The host-bridge test reads `lib/plugins/view/plugin_sdk_scripts.dart` from `OTZARIA_SOURCE_ROOT`. To package from an Otzaria source checkout with its Flutter dependencies installed:

```sh
SHIUR_PLUGIN_ROOT=/path/to/ShiurListener/player flutter test /path/to/ShiurListener/player/tests/package_plugin_test.dart
```

No Otzaria native source is modified for 1.4.1. The developer handoff identifies the inspected upstream commit and separates current features from proposed host work.

The actual-file-server integration test also needs ffmpeg to generate its real WAV fixture. From the Otzaria checkout, run `SHIUR_PLUGIN_ROOT=/path/to/ShiurListener/player OTZARIA_SOURCE_ROOT=/path/to/otzaria flutter test /path/to/ShiurListener/player/tests/real_host_media_test.dart`. These remain development prerequisites only.
