# Shiur Player downloads

## Current standalone: 0.8.2

[Download setup](shiur-player-setup-0.8.2.exe) or Check for updates. Custom player branding, no Favorites section, and Rename recording with saved-place/bookmark/collection preservation. Both speed buttons cycle 1× → 1.5× → 2× → 0.5× → 1×.

## Standalone: 0.8.1

[Download setup](shiur-player-setup-0.8.1.exe) or Check for updates. Main and mini speed buttons cycle exactly 1× → 1.5× → 2× → 0.5× → 1×, overriding obsolete cycle preferences. Saved positions carry over.

## Standalone: 0.8.0

[Download setup](shiur-player-setup-0.8.0.exe) or use Check for updates. Light styling with rounded controls and corrected half-speed mini-player cycle, including migration of existing settings. Saved places carry over. [Screenshot](../previews/shiur-player-0.8.0.png).

## Standalone: 0.7.0

Download **[shiur-player-setup-0.7.0.exe](shiur-player-setup-0.7.0.exe)** or click **Check for updates** in standalone 0.6.0. No extraction. New full-width library, permanent playback dock, Favorites, queue editing, section repeat, sleep presets, profile backups and clickable mini-player progress. Existing standalone positions carry over. [Full guide](../standalone/README.md). Earlier variants below are retained for reference. Actual Windows setup/rendering and speaker output remain unverified here.

The current plugin-only build is **1.4.0**. Install `shiur-player-1.4.0.otzplugin` in Otzaria as an update, keep its existing data and restart Otzaria. Add a local recording or folder, wait for it to load, and press Play. No companion installation is required.

Version 1.4.0 has a simpler interface, startup/file retry, preservation of saved positions, malformed-queue recovery, and a bundled sound check under **עזרה**. The [installation guide](../player/README.md) explains recovery steps and the [Hebrew developer handoff](../docs/OTZARIA_AUDIO_HANDOFF.he.md) explains the host work needed for other tabs and floating controls.

The plugin-only player must remain visible. The companion ZIP is the older independent-playback comparison build and includes its separately named Otzaria plugin, Python and reduced VLC runtime. Extract the whole ZIP before running Shiur Player.exe. Choose a folder, install the included plugin, open נגן מלווה and connect using the displayed pairing code. The companion remains running after Otzaria closes.

Both plugin IDs can remain installed. Their libraries and positions are separate. `shiur-player-1.3.0.otzplugin` is kept here as an older build; use 1.4.0 for the update.

These builds are experimental. Browser/service/package checks pass; actual Otzaria desktop integration and the companion Windows executable still need real-device verification. Physical audio output is unverified here. See the installation guide for the exact scope of the tests.

## Sidekick 1.0.0 facelift

Use **sidekick-windows-x64-1.0.0.zip** for the updated companion, with **Sidekick.exe** and **sidekick-1.0.0.otzplugin** inside. Close the old companion first, extract the whole ZIP, and install the plugin as an update to preserve its data. The old companion ZIP is retained as an older build. [Setup and testing](../sidekick/README.md).

## Inside 1.4.1

Use **inside-1.4.1.otzplugin**. It clearly shows Inside 1.4.1 in its heading and uses the same visible-page audio engine as 1.4.0. The reported message about blocked sound “במופע הרקע” was traced to the older 1.2 background player. Install as an update, fully quit Otzaria, reopen it, and open Inside from the plugins list. Confirm its heading. Do not uninstall or clear saved data. An integration check with the real Otzaria file server passed.

## Companion 1.1.0 — נגן שיעורים / Shiur Player

Use **sidekick-windows-x64-1.1.0.zip**. It includes a console-free GUI launcher and **sidekick-1.1.0.otzplugin**. Close the old companion, extract the whole ZIP, choose the actual recordings folder in the normal app window, and connect. Both interfaces support Hebrew/English. Rescan discovers newly added files. The code form and setup window hide after connection. Exit player stops the service. Update both parts from the same ZIP; keep existing data. [Full instructions](../sidekick/README.md).

## Standalone Windows app 0.1.0 — previous build

Download **shiur-player-windows-x64-0.1.0.zip** for the English-only standalone desktop player. Extract the complete ZIP and open **Shiur Player.exe**. Choose a recordings folder once; after a restart, open the app and press Play. No Otzaria, plugin, pairing code or connection service is needed. A separate standalone profile leaves earlier Inside/Sidekick data untouched. The native Windows interface remains unverified on a real Windows desktop; see [the guide](../standalone/README.md).

## Standalone Windows app 0.2.0 — redesigned player

Download **shiur-player-windows-x64-0.2.0.zip**. Extract everything and run **Shiur Player.exe**. The new library shows a separate resume time for every shiur, with recent-first Continue listening and a dedicated Now Playing panel. It reuses standalone 0.1.0 positions. No separate runtime installation. [Instructions](../standalone/README.md). Windows desktop execution remains unverified.

## נגן שיעורים 1.4.2 — plugin display name

Use **shiur-player-1.4.2.otzplugin** to replace the former Inside name with **נגן שיעורים** in the plugin list, tab, heading and error details. Install as an update and restart Otzaria. Same plugin ID and saved-data keys; no playback-engine changes.

## Standalone Windows app 0.3.0 — flat controls and automatic mini player

Download **shiur-player-windows-x64-0.3.0.zip**. This update removes decorative slogans, replaces old scrollbars and sliders, simplifies collection assignment into one dialog, and shows the floating mini player automatically when minimized. Existing standalone listening positions carry over. Extract the entire ZIP. Windows desktop execution remains unverified here.

## Standalone Windows app 0.4.0 — library and keyboard improvements

Download **shiur-player-windows-x64-0.4.0.zip**. Select several recordings and add them to a collection in one action, sort by column, and use right-click actions. Window size and sorting are remembered. Space on a focused button no longer triggers playback twice; skipping during loading uses the saved resume position. Existing standalone positions carry over. Extract the entire ZIP and run Shiur Player.exe. Actual Windows GUI and speaker output remain unverified here.

## נגן שיעורים 1.4.3 — author metadata

Download **shiur-player-1.4.3.otzplugin**. The manifest credits **DanTheMAn** as author. Install as an update. Plugin ID, permissions, saved-data keys and playback code are unchanged.

## נגן שיעורים 1.4.4 — publishing review

Download **shiur-player-1.4.4.otzplugin**. Author **DanTheMAn**, project homepage and explicit experimental stability are included. The official validator built the archive and validated its contents against the current SDK specification: zero errors, warnings or design findings. [Upload requirements and sources](../player/STORE_UPLOAD.md). No store submission was performed.

## נגן שיעורים 1.4.5 — author spelling

Download **shiur-player-1.4.5.otzplugin**. The author is exactly **DanTheMan**. All other manifest settings and playback behavior are retained. The official validator passes with zero errors or warnings. [Screenshot](../previews/shiur-player-plugin-1.4.5.png).

## Standalone Windows app 0.5.0 — stronger contrast and resizable mini player

Download **shiur-player-windows-x64-0.5.0.zip**. Bold navy/blue styling, a clear Mini player button, locked column dividers, and a smaller resizable floating player with saved size/position and clickable speed. Settings offers 0.5× or 1.5× speed-cycle steps. Repeated idle redraws and the floating player’s full-window erase loop were removed. Existing saved positions carry over. [Preview](../previews/shiur-player-0.5.0.png). Windows GUI and physical audio remain unverified here.

## Standalone Windows app 0.5.1 — preferred speed cycle

Download **shiur-player-windows-x64-0.5.1.zip**. The mini-player speed button now defaults to **1× → 1.5× → 2× → 1.5× → 1×**. The half-speed cycle remains an option in Settings. All 0.5.0 visual, resizing and redraw improvements are retained.

## Standalone Windows app 0.6.0 — installer and updates

Run **shiur-player-setup-0.6.0.exe** once. It creates desktop/Start menu shortcuts and preserves the existing standalone profile. Future updates use **Check for updates** inside the app. The portable ZIP remains optional. Updates contact only the fixed GitHub release channel when requested; no browser opens. Actual Windows setup and restart remain unverified here.
