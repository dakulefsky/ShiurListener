# ShiurListener — נגן שיעורים

A Hebrew local-shiur player for Otzaria 0.9.98 or newer.

## Download

- **[Plugin-only player 1.4.0](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-1.4.0.otzplugin)** — redesigned controls, recovery actions, saved positions and a bundled sound check. Install directly in Otzaria; no companion is required.
- [Windows companion ZIP](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-companion-windows-x64.zip) — the earlier experimental comparison build, including its runtime and a separately named plugin.
- [Plugin source and developer documents](https://raw.githubusercontent.com/dakulefsky/ShiurListener/main/downloads/shiur-player-source-1.4.0.zip).
- [Checksums](downloads/SHA256SUMS.txt).

## Install the plugin-only player

1. Install **shiur-player-1.4.0.otzplugin** as an update in Otzaria. Keep existing plugin data; do not uninstall first.
2. Restart Otzaria once and allow reading user-selected files.
3. Click **הוספת שיעור** or **ייבוא תיקייה**. Wait for **מוכן לניגון**, then press **ניגון**.
4. If there is a problem, use **ניסיון נוסף**, or open **עזרה** and click **השמעת צליל בדיקה**. The help panel includes a direct audio strip. Expanded error details include the player version.

The first new recording loads silently; selecting a recording does not automatically start sound. Existing folders, bookmarks and per-shiur positions are retained on update. The new layout puts playback controls first and moves less-used actions into menus.

![Player 1.4.0](previews/player-1.4.0.png)

For reading while listening, right-click the player tab, choose **הצג לצד**, then choose an open book. Keep the player pane visible. **נגן קטן** reduces the controls. Hiding the player or minimizing Otzaria may pause it.

## Instructions for Otzaria developers

[Hebrew handoff: playback across tabs, floating controls and global shortcuts](docs/OTZARIA_AUDIO_HANDOFF.he.md).

It includes a forwardable request, inspected host code paths, a proposed native audio API, permission boundaries, cross-platform floating-window requirements and acceptance tests. These are proposed host changes; the plugin does not claim to implement them by itself.

[Plugin source, installation details and verification](player/README.md). No Otzaria native source is modified by the 1.4.0 update.

## Companion comparison

Extract the entire companion ZIP, run **Shiur Player.exe**, choose a recordings folder and copy its pairing code. Install the included comparison plugin, approve its local connection permission, open **נגן מלווה**, choose **נגן מלווה · האזנה ברקע**, and connect using that code.

The companion plays independently of the visible Otzaria tab. It includes a Windows floating bar and global shortcuts. Both plugins can remain installed, with separate libraries and positions. Closing Otzaria leaves the companion playing; close the companion window to stop it.

## Verification and limitations

Version 1.4.0 passes eight persistence regressions, real-WAV Chromium tests with click restrictions enabled, and a test using Otzaria's actual JavaScript bridge with a file-origin page and separate loopback media server. Startup retry, preservation after failed library reads, old-WebView UUID compatibility and missing-recording recovery are covered. The actual Otzaria packager validates its manifest and design.

The exact cause of the user's original installation failure has not been established without its error message. The updated build has not been run in an installed Windows/macOS/Linux Otzaria application. Browser playback tests do not verify physical speaker output.

The companion Windows executable, floating bar and global shortcuts also remain unverified on a Windows computer. Its service and VLC decoding checks ran on Linux; VLC checks used a dummy audio output.

The plugin has no external network or browser-opening permission. The companion is not a device browser-lockdown tool: it bundles a general Python interpreter. Runtime licenses and source URLs are included in its ZIP.
