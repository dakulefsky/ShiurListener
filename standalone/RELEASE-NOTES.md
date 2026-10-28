# Shiur Player 0.9.11

Fixes startup when an existing saved profile contains a setting or value the current build cannot validate. Before attempting recovery, the app makes a byte-for-byte backup named `state.json.recovery-YYYYMMDD-HHMMSS.bak` beside the original profile. It then recovers individually valid settings and shiur positions, leaving malformed entries out rather than resetting the entire library. If the JSON itself is damaged, the complete original remains in the recovery backup.

Existing listening positions and settings are preserved wherever they can be safely validated. This release does not delete or overwrite the original recovery copy.
