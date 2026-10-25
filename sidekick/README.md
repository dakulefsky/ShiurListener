# Sidekick 1.0.0

The separate companion player, with a Hebrew Otzaria controller, simplified connection card, prominent playback controls and a refreshed native Windows floating bar. Inside remains a separate player and plugin.

## Install or update

Close the old companion, extract the complete Windows ZIP into a new folder, run **Sidekick.exe**, and select your recordings folder. Install the included **sidekick-1.0.0.otzplugin** in Otzaria as an update. Open the **Sidekick** tab, paste the pairing code and press **חיבור**. The connection card collapses on success. **הגדרות חיבור** reopens it. Keep the companion running.

No separate Python or VLC installation is needed. The plugin retains ID `org.shiurplayer.companion`; the backend protocol and data directory are unchanged. Existing Sidekick folders, positions and optional remembered-connection settings are reused. Do not uninstall the plugin or delete its data before updating. Restarting the companion creates a new pairing code. Inside has separate data.

## Appearance

The Sidekick controller opens directly into companion mode. Connection steps are grouped separately from listening. Play/Pause, skip, speed and volume are together at the top, with the recording library below. Timer, automatic next recording and bookmarks are under a disclosure. The interface follows Otzaria's palette and injected font, including dark mode and narrow panes.

The native Windows bar has larger rounded buttons, more spacing, elapsed time, speed and Sidekick branding. It retains always-on-top/non-activating flags, remembered position and hide/reopen behavior. Its actual Windows rendering is not verified here.

## Checks and limits

Six service/browser tests pass, covering pairing/reconnection, folders, positions, speeds, skips, bookmarks, keyboard controls, sleep timer and continued queue advancement while the plugin is suspended. The browser test captures light, dark and narrow layouts. Two mocked Win32 tests cover floating-bar labels, transport, hide/reopen and window flags. The real Otzaria packager validates the manifest and design. Archive integrity, source correspondence, x64 PE structure and unchanged runtime/license files are verified.

The Windows executable and physical audio output have not been exercised on a Windows machine. The backend is unchanged from the earlier build, whose real-VLC decoder tests ran on Linux with a dummy output. No new Mac/Linux executable is provided by this facelift.

There is no browser viewer or URL-opening endpoint. The authenticated service binds only to `127.0.0.1:18473`. The bundled Python runtime is general purpose; Sidekick does not enforce device-wide browser restrictions.

## Develop

`plugin/` is the Otzaria interface; `companion/` contains the Python backend, native floating bar, shortcuts and private Rubik font. Installed users do not need development tools.

```sh
python tests/test_companion.py
python tests/test_floating_bar.py
```

The browser test needs Playwright/Chromium. From an Otzaria source checkout with Flutter dependencies installed:

```sh
SIDEKICK_ROOT=/path/to/ShiurListener/sidekick flutter test /path/to/ShiurListener/sidekick/tests/package_plugin_test.dart
```

Compile the launcher with Go (`GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o 'build/windows/Sidekick.exe' build/windows/launcher.go`). Reuse the previous portable ZIP as the licensed runtime base:

```sh
python build/package_sidekick.py --base /path/to/shiur-player-companion-windows-x64.zip
```

The packager preserves the runtime and upstream notices, replaces the launcher/UI/floating-bar sources, and verifies the resulting archive. Runtime source URLs and original hashes remain in BUILD-INFO.json. The audio backend and storage format are unchanged.
