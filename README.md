# ShiurListener

Experimental shiur players for Otzaria 0.9.98 or newer.

## Downloads

- [Windows companion ZIP](https://github.com/dakulefsky/ShiurListener/releases/download/comparison-v1/shiur-player-companion-windows-x64.zip) — includes the companion program, Python, a reduced VLC runtime, and a separately named Otzaria plugin.
- [Plugin-only player 1.3.0](https://github.com/dakulefsky/ShiurListener/releases/download/comparison-v1/shiur-player-1.3.0.otzplugin) — install directly in Otzaria and keep its player pane visible.
- [Release notes and checksums](https://github.com/dakulefsky/ShiurListener/releases/tag/comparison-v1).

## Companion setup (Windows x64)

1. Extract the entire ZIP and run **Shiur Player.exe**.
2. Choose your recordings folder and copy the pairing code from the companion window.
3. Install the included **shiur-player-companion-compare.otzplugin** in Otzaria. Approve its local connection permission.
4. Open **נגן מלווה**, click **נגן מלווה · האזנה ברקע**, paste the code, and click **חיבור**.
5. Choose a shiur. Keep the companion window running. Closing Otzaria leaves it playing; close the companion window to stop it.

The companion handles playback independently of the visible Otzaria tab. It includes a Windows floating control bar and global shortcuts. The companion and plugin-only player have separate plugin IDs and can remain installed together. They keep separate libraries and listening positions.

## Plugin-only setup

Install **shiur-player-1.3.0.otzplugin** in Otzaria. Restart Otzaria when updating from an older hidden-background player. Select a recording, wait for it to load, and press Play. Open a book and use the player tab's **הצג לצד** menu to keep both visible. **נגן קטן** switches to compact controls. Hiding the player or minimizing Otzaria may pause playback.

## Testing and limitations

These are experimental builds. Companion service and Chromium control tests pass. The ZIP and x64 launcher structure were verified, but the Windows executable, audible output, floating bar and Windows shortcuts have not been tested on a Windows computer. Actual VLC decoding was tested on Linux with a dummy audio output.

The plugin-only player passed real-audio browser tests with user-activation restrictions enabled. Those tests do not verify an actual Otzaria Windows installation.

The companion has no browser interface or URL-opening API. It is not a browser or Internet lockdown tool: bundled Python is a general interpreter. Device restrictions must be enforced through operating-system and network policy. Runtime licenses and source URLs are included in the ZIP.
