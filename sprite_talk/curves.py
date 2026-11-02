"""Motion curves.

GENERIC_LOOP is a synthetic 25-frame (0.83 s at 30 fps) talk loop, stored as
plain numbers in units of *head height* (hair top -> chin). ``dy`` is in
"silhouette-dip" units (how far the top of the head drops); the renderer
multiplies it by ``dy_gain`` (default 0.75, see README) before warping.
It is a hand-built parametric curve (|sin| dip + phase-shifted sway), not
traced from any third-party footage. Replace it with your own via
``sprite-talk calibrate``.
"""
import json
import numpy as np

FPS_REF = 30
# fmt: off
GENERIC_LOOP = {
    "fps": 30,
    "units": "head_height",
    "dx": [0.0000, 0.0040, 0.0077, 0.0110, 0.0135, 0.0152, 0.0160, 0.0157, 0.0145, 0.0123, 0.0094, 0.0059, 0.0020, -0.0020, -0.0059, -0.0094, -0.0123, -0.0145, -0.0157, -0.0160, -0.0152, -0.0135, -0.0110, -0.0077, -0.0040],
    "dy": [0.0000, 0.0146, 0.0287, 0.0417, 0.0530, 0.0624, 0.0693, 0.0736, 0.0750, 0.0736, 0.0693, 0.0624, 0.0530, 0.0417, 0.0287, 0.0146, 0.0000, 0.0068, 0.0129, 0.0173, 0.0197, 0.0197, 0.0173, 0.0129, 0.0068],
}
# fmt: on


def load_curve(path=None):
    if path is None:
        return GENERIC_LOOP
    with open(path) as f:
        return json.load(f)


def bob_series(n, head_px, curve=None, fps=30, amp=1.0, dy_gain=0.75, talking=None, ease_frames=6):
    """Return (dx, dy) arrays in pixels for ``n`` frames.

    Amplitude scales with on-screen head height ``head_px``. ``talking`` is an
    optional bool array; the loop fades in/out (``ease_frames``) around speech so
    the body settles when silent.
    """
    c = curve or GENERIC_LOOP
    dx0 = np.asarray(c["dx"], float)
    dy0 = np.asarray(c["dy"], float)
    src_fps = c.get("fps", FPS_REF)
    t = np.arange(n) * src_fps / fps
    idx = np.arange(len(dx0))
    L = len(dx0)
    dx = np.interp(t % L, np.r_[idx, L], np.r_[dx0, dx0[0]])
    dy = np.interp(t % L, np.r_[idx, L], np.r_[dy0, dy0[0]])
    env = np.ones(n)
    if talking is not None:
        tk = np.asarray(talking, float)[:n]
        k = np.ones(2 * ease_frames + 1) / (2 * ease_frames + 1)
        env = np.clip(np.convolve(tk, k, "same"), 0, 1)
    s = head_px * amp * env
    return dx * s, dy * s * dy_gain
