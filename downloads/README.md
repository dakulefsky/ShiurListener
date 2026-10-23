Experimental comparison builds for Otzaria 0.9.98 or newer.

Download **shiur-player-companion-windows-x64.zip** for the portable Windows companion. Extract the whole ZIP, run Shiur Player.exe, choose your recordings folder, and install the included comparison .otzplugin in Otzaria. Open נגן מלווה, choose נגן מלווה · האזנה ברקע, and connect using the pairing code shown in the companion window. Python and the reduced VLC runtime are included.

Download **shiur-player-1.3.0.otzplugin** for the plugin-only player. Install it in Otzaria, restart Otzaria if updating from the older hidden-background player, select a recording and press Play. Keep the player visible, using Otzaria’s הצג לצד menu to read alongside it.

The comparison companion plugin has a separate ID, so both can remain installed. Their libraries and listening positions are separate. Closing Otzaria leaves the companion running; close the companion window to stop it.

Validation: companion service and Chromium controls tests pass, package integrity and x64 launcher structure are verified. The companion Windows executable, physical audio output, floating bar and global shortcuts have not been tested on a Windows machine. The plugin-only player passed real-audio Chromium tests with user-activation restrictions enabled; actual Otzaria Windows integration is unverified.

The companion has no browser interface or URL-opening API, but is not a device lockdown tool. Its bundled Python is a general interpreter. Runtime licenses and source URLs are included in the ZIP. SHA256SUMS.txt provides file checksums.
