# Shiur Player downloads

The current plugin-only build is **1.4.0**. Install `shiur-player-1.4.0.otzplugin` in Otzaria as an update, keep its existing data and restart Otzaria. Add a local recording or folder, wait for it to load, and press Play. No companion installation is required.

Version 1.4.0 has a simpler interface, startup/file retry, preservation of saved positions, malformed-queue recovery, and a bundled sound check under **עזרה**. The [installation guide](../player/README.md) explains recovery steps and the [Hebrew developer handoff](../docs/OTZARIA_AUDIO_HANDOFF.he.md) explains the host work needed for other tabs and floating controls.

The plugin-only player must remain visible. The companion ZIP is the older independent-playback comparison build and includes its separately named Otzaria plugin, Python and reduced VLC runtime. Extract the whole ZIP before running Shiur Player.exe. Choose a folder, install the included plugin, open נגן מלווה and connect using the displayed pairing code. The companion remains running after Otzaria closes.

Both plugin IDs can remain installed. Their libraries and positions are separate. `shiur-player-1.3.0.otzplugin` is kept here as an older build; use 1.4.0 for the update.

These builds are experimental. Browser/service/package checks pass; actual Otzaria desktop integration and the companion Windows executable still need real-device verification. Physical audio output is unverified here. See the installation guide for the exact scope of the tests.
