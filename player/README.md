# נגן שיעורים — development source 1.6.0

Author: **DanTheMan**. Current source is 1.6.0 in development, with fast two-excerpt offline analysis and bounded MP3/WAV reads. No 1.6.0 download has been published. The current packaged download remains 1.5.0. See [the browser development results](experiments/browser-two-check/README.md) for actual measurements, supported formats and limits.

A Hebrew Otzaria player for local shiurim, with a simpler layout, separate saved listening positions and recovery controls. Install the plugin directly; no companion, Python or VLC installation is needed.


## Store upload requirements

See [the publishing review](STORE_UPLOAD.md) for the official sources, field requirements, validation results and first-upload requirements. Published packages were built and checked with the official Otzaria validator; the current development source has been validated without publishing a new archive; the repository now checks manifest metadata and runs the official validator in CI with store publishing explicitly disabled.

## Recognizing the correct player

Current development source shows **נגן שיעורים 1.6.0**, including in compact mode; existing published versions show their own release numbers. The Hebrew error “מנוע הדפדפן של אוצריא חסם שמע ללא לחיצה במופע הרקע. בגרסה זו נדרש שינוי מדיניות באוצריא.” was found in the old 1.2 background player's `background.js`; it is absent from the visible-page player. Seeing it means that older UI/code is running.

Install this package as an update, fully quit Otzaria (including its tray instance if it remains running), reopen it and open **נגן שיעורים** from the plugin list. Do not uninstall or clear data. If the heading does not say נגן שיעורים 1.4.5, the new page is not running yet. This update replaces the former Inside display name with נגן שיעורים in the plugin list, tab, page heading and error details. The plugin ID and storage keys are unchanged. The audio engine is unchanged.

## Install and listen

1. Download `shiur-player-1.4.5.otzplugin` and install it in Otzaria as an update. Do not uninstall the existing plugin or clear its data first.
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

No Otzaria native source is modified for 1.4.5. The developer handoff identifies the inspected upstream commit and separates current features from proposed host work.

The actual-file-server integration test also needs ffmpeg to generate its real WAV fixture. From the Otzaria checkout, run `SHIUR_PLUGIN_ROOT=/path/to/ShiurListener/player OTZARIA_SOURCE_ROOT=/path/to/otzaria flutter test /path/to/ShiurListener/player/tests/real_host_media_test.dart`. These remain development prerequisites only.

## 1.4.6: minimum recording duration

Only recordings of at least five minutes can play. Unknown/non-finite duration is blocked, including through direct controls. Short shiurim also fail; long music can pass. The fixed diagnostic sound remains available. This does not enforce host-level media restrictions or identify speech/music. See [the developer policy note](../docs/INSIDE_MEDIA_POLICY.md). Author remains DanTheMan; plugin ID and saved data keys are unchanged.

## 1.5.0: bundled offline speech/music filter

The plugin now bundles YAMNet, TensorFlow.js 4.9.0 and the TensorFlow Lite WebAssembly runtime. No Python, companion app, cloud analysis, CDN access, or first-run model download is required. Imported recordings stay muted and unplayable until minimum-duration validation and local analysis finish. Progress is shown in Hebrew. Clear music and overall uncertain results are blocked; predominantly speech can pass under the balanced experimental rule. Three consecutive music-hit frames (approximately 2.9 seconds) or at least 10% music-hit coverage blocks the recording. This is one pretrained detector plus aggregation, not a second independently trained classifier. Brief candidates below these thresholds can pass.

Approved analysis is cached locally against the complete file SHA-256 and policy version; new content is re-read and rehashed before cache lookup. This is plugin-level filtering, not tamper-resistant host enforcement. Existing saved positions are reused. The fixed bundled sound-check tone is separate from imported recordings.

Current resource limits: 40 MiB encoded file, at most 90 minutes, and at most 48 million decoded channel samples. Decode uses a browser OfflineAudioContext at 16 kHz. The full decoded recording is held in memory; long stereo recordings can exceed the sample limit before 90 minutes. There is no streaming decoder or full process-resource isolation. Unsupported decoding, missing runtimes, model checksum mismatch and failed analysis do not permit playback.

Actual Chromium tests ran with all requests outside the local test server blocked: a full spoken recording was analyzed and played, a five-minute music recording was blocked, short files were blocked, saved positions and keyboard controls remained functional. Twenty-four Node tests pass. The official validator accepts source and archive with no errors/warnings/design violations. Actual installed Otzaria/WebView support and physical sound still need a device check; unsupported environments report an error instead of bypassing analysis.

Developer browser tests require Playwright and FFmpeg plus local reference files selected through `SHIUR_TEST_SPEECH` and `SHIUR_TEST_MUSIC`. Neither reference recording is bundled or uploaded by the plugin.
