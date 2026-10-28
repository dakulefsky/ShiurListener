# Shiur Player 0.9.21

Fixes mini-player seek behavior so both the normal progress strip and the hover-to-scrub control respond to a click, not only a drag. Moves the collapsed mini-player's stacked expand/close controls farther from the right edge so they no longer block resizing from that side.

Fixes the Settings → Audio enhancements transition by opening the next dialog after the current click callback completes. Long settings labels now wrap responsively instead of being clipped in narrower windows. Mouse clicks no longer leave persistent keyboard-focus rings around custom buttons, switches, and sliders; keyboard navigation remains supported.

Existing listening positions, collections, bookmarks and original recordings are preserved. Offline speech enhancement remains optional and runs locally.
