"""Render a talking-head mp4 from a sprite set + voice track."""
import subprocess
import numpy as np
from .sprites import SpriteSet
from .warp import BodyWarp
from .curves import bob_series, load_curve
from .mouth import audio_rms, audio_duration, mouth_levels, load_alignment, viseme_track
from .blink import blink_schedule

LEVEL_KEYS = ("closed", "small", "large")


def render(sprites_cfg, audio, out, fps=30, curve=None, amp=1.0, dy_gain=0.75, piv_ratio=0.355,
           alignment=None, visemes=False, bg=(0, 0, 0), seed=0, dur=None, crf=18, preset=None,
           head_px=None, chin_y=None):
    S = SpriteSet(sprites_cfg)
    dur = dur or audio_duration(audio)
    n = int(round(dur * fps))
    rms = audio_rms(audio, fps, dur)
    align = load_alignment(alignment) if alignment else None
    lvl, env = mouth_levels(rms, n, fps, align)
    if visemes and align:
        vis = viseme_track(align, n, fps)
        mouths = [("closed" if v == "X" or lvl[i] == 0 and v not in ("MBP", "F") else v) for i, v in enumerate(vis)]
        mouths = [m if (m in S.mouth) else LEVEL_KEYS[lvl[i]] for i, m in enumerate(mouths)]
    else:
        mouths = [LEVEL_KEYS[l] for l in lvl]
    blinks = blink_schedule(n, fps, seed=seed)
    eye_key = {1: "half", 2: "closed"}
    W = BodyWarp.for_sprite(S.base, piv_ratio=piv_ratio)
    talking = env > 0.08
    if preset:
        from .presets import PRESETS, series_for_preset, LinearPinWarp
        pp = PRESETS[preset]
        top = W.top
        hh = head_px or (chin_y - top if chin_y else W.head_height / 0.355 * 0.5)  # fallback: chin ~ half silhouette
        chin = chin_y or top + hh
        W = LinearPinWarp(S.base.shape, chin - pp["rigid_above_chin"] * hh, S.H - 1)
        W.head_height = hh
        dx, dy, _ = series_for_preset(preset, n, hh, talking, fps, amp, env=env)
    else:
        dx, dy = bob_series(n, W.head_height, load_curve(curve), fps, amp, dy_gain, talking)
    H, Wd = S.H - S.H % 2, S.W - S.W % 2
    bgc = np.array(bg, np.float32)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{Wd}x{H}",
                          "-r", str(fps), "-i", "-", "-i", str(audio), "-t", f"{dur:.3f}", "-c:v", "libx264",
                          "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", str(out)],
                         stdin=subprocess.PIPE)
    for f in range(n):
        im = W(S.frame(mouths[f], eye_key.get(blinks.get(f, 0))), dx[f], dy[f])
        a = im[..., 3:4].astype(np.float32) / 255
        rgb = (im[..., :3] * a + bgc * (1 - a)).astype(np.uint8)
        p.stdin.write(np.ascontiguousarray(rgb[:H, :Wd]).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise RuntimeError("ffmpeg failed")
    return dict(frames=n, preset=preset, head_px=round(W.head_height, 1), piv=round(getattr(W, 'piv', getattr(W, 'rigid_y', 0)), 1),
                frac_open=round(float((lvl > 0).mean()), 3), blinks=len([1 for v in blinks.values() if v == 2]))
