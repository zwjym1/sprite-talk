"""sync_measure: cross-correlate mouth openness in a rendered video against
audio loudness. Best lag 0..-1 frames (mouth slightly leading) reads as in sync."""
import subprocess
import numpy as np
from .mouth import audio_rms


def mouth_signal(path, box, dur=None, mode="dark", thr=90):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)] + (["-t", str(dur)] if dur else [])
    cmd += ["-vf", f"crop={w}:{h}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    v = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.uint8).reshape(-1, h, w, 3).astype(int)
    if mode == "red":  # pink/red mouth interior
        m = (v[..., 0] > 140) & (v[..., 1] < 150) & (v[..., 0] - v[..., 1] > 60) & (v[..., 2] > 70)
    else:  # dark mouth interior / outline
        m = v.mean(-1) < thr
    return m.sum((1, 2)).astype(float)


def xcorr(a, b, maxlag=10):
    n = min(len(a), len(b))
    a = a[:n] - a[:n].mean()
    b = b[:n] - b[:n].mean()
    out = {}
    for L in range(-maxlag, maxlag + 1):
        x = a[max(0, L):n + min(0, L)]
        y = b[max(0, -L):n - max(0, L)]
        out[L] = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0
    return out


def measure(video, box, fps=30, dur=None, mode="dark", thr=90):
    m = mouth_signal(video, box, dur, mode, thr)
    r = audio_rms(video, fps, dur)
    c = xcorr(m, r)
    L = max(c, key=c.get)
    mid = (m.min() + m.max()) / 2
    return dict(frames=len(m), corr_at_0=round(c[0], 3), best_lag_frames=L, corr_best=round(c[L], 3),
                mouth_px_min=int(m.min()), mouth_px_max=int(m.max()), frac_open=round(float((m > mid).mean()), 3))
