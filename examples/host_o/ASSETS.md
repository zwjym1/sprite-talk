# Host O example assets

Original character (AI-generated, no third-party art). Demo/testing use with the
same MIT license as the package.

Mirrors `examples/host_a/`: face-crop overlays at `overlay_offset`, not whole-body stickers.

- `sprites/base.png`: full-body still, **770×1080**, RGBA, dark background
- `sprites/m_closed.png`, `m_E.png` (small), `m_A.png` (large): **360×360** face crops at `overlay_offset` `[215, 340]`
  - Closed = base smile (exact). Small/large = mouth_v5 face-edit opens (boy line weight; Aning open/close *structure* only), pixel-locked onto base outside the mouth ROI
- `sprites/e_half.png`, `e_closed.png`: blink crops (same placement). Half is a synthesized half-lid from base×closed; closed is a locked blink edit
- `vo.mp3`: host_d intro VO (~10.7 s). No `vo_timings.json` yet (optional; render works loudness-only)

## Measure (770×1080)

```json
{
  "overlay_offset": [215, 340],
  "mouth_roi": [330, 566, 461, 678],
  "eye_roi": [265, 492, 533, 600]
}
```

## Render

```bash
sprite-talk render examples/host_o/sprites.json examples/host_o/vo.mp3 \
  -o out/host_o_talk.mp4 --preset aning_dyn --head-px 513 --chin-y 669 --seed 7
# default preset in library remains unchanged for callers that omit --preset
sprite-talk sync out/host_o_talk.mp4 --box 336,572,448,672
```

Compressed sample render: [`demo.mp4`](demo.mp4).

Pose cuts (separate from talking bob): `hosts/host_o_star_sleep/poses_kit/` +
`samples/host_o_posekit_swap_sample.mp4` (same polished mouth patches, hard pose cuts + sprite-talk bottom-anchored bob per pose; blink_v2 face-edit eyes).
