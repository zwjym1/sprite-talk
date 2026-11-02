# Host O — remaining gap vs host_a “perfect”

What’s already at host_a workflow quality:
- Face-crop overlays + `sprites.json` ROIs (not whole-body redraw stickers)
- 3-level volume mouths + blinks + bottom-anchored bob (`--dy-gain 0.75`)
- Mouths are boy line-weight face-edits (no pink girl lips; no leftover smile whiskers on paste)
- Sync on talk.mp4: **best_lag = −1 frame**, corr_best ≈ **0.64** (dark mode, box `336,572,448,672`) — at or above host_a demo (~0.32)

Still short of host_a polish (optional follow-ups):
1. **No forced-alignment file** for this VO — syllable-closed flaps are loudness-only. Add `vo_timings.json` (or `sprite-talk align`) to match host_a’s consonant snaps.
2. **Half-blink is synthesized**, not a face-edit redraw like host_a’s `e_half`. Fine in motion; a true half-lid edit would match host_a art pipeline 1:1.
3. **`eyes_closed` source** still shows mild patch/skin grain vs base under tight zoom; sprite-talk feather hides it in video. A cleaner blink face-edit would remove the last grain.
4. **Posekit face match** on `pose_think` / `pose_react_surprise` is ~0.79–0.81 (idle/point/peace ≥0.90). Warped mouths look OK; tighter pose alignment or per-pose mouth locks would help those cuts.
5. **open_s cavity** is intentionally small (boy smile → slight oval). If VO needs a clearer mid level, a slightly taller open_s face-edit would separate small vs large more like host_a’s E vs A.

Not gaps: girl-lip color, smile whiskers, whole-body mouth stickers — those were fixed in mouth_v5 and carried into this example.
