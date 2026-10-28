# Shiur Player 0.9.13

Fixes the collapsed mini-player resize interaction. Resize edges and corners now take priority over nearby controls, and hover expansion is suppressed while the pointer is near a resize edge. This prevents the pill from growing away from the cursor while you try to grab a corner to make it smaller. Skip controls still appear when hovering away from the resize borders.

Includes the prior 0.9.12 fixes and optional offline speech enhancement. Enhanced audio is processed locally, cached separately, and never overwrites the original recording. Results vary by recording; this is not guaranteed vocal/music separation.

Existing listening positions, collections, bookmarks and audio files are preserved.
