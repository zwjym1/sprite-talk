"""Bottom-anchored body warp.

Every pixel is displaced by w(y) * (dx, dy):
    w(y) = clip((bot - y) / (bot - piv), 0, 1) ** gamma
Rows above ``piv`` (the head block) move rigidly, rows between ``piv`` and
``bot`` fall off linearly (gamma=1) and the feet / frame bottom stay pinned.
No rotation, no scale pulse: the reference fit found both negligible.
"""
import numpy as np
import cv2


def falloff_weight(y, piv, bot, gamma=1.0):
    return np.clip((bot - y) / max(1e-6, bot - piv), 0.0, 1.0) ** gamma


def silhouette_bbox(img, thr=45):
    """(top, bottom) rows of the character. Uses alpha if present, else max(RGB)>thr."""
    a = np.asarray(img)
    if a.shape[-1] == 4 and a[..., 3].min() < 250:
        m = a[..., 3] > 16
    else:  # opaque image: assume a dark / plain background
        m = a[..., :3].max(-1) > thr
    rows = np.where(m.any(1))[0]
    return (int(rows[0]), int(rows[-1])) if len(rows) else (0, a.shape[0] - 1)


class BodyWarp:
    """Warp a sprite with a rigid head block and linear falloff to pinned feet.

    piv_ratio: pivot position as a fraction of visible height measured from the
               silhouette top (0.355 = just under the chin for typical chibi /
               bust-up proportions). Override with ``piv`` in pixels.
    """

    def __init__(self, shape, top=None, bot=None, piv=None, piv_ratio=0.355, gamma=1.0):
        h, w = shape[:2]
        self.top = 0 if top is None else top
        self.bot = h - 1 if bot is None else bot
        self.piv = piv if piv is not None else self.top + piv_ratio * (self.bot - self.top)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.w = falloff_weight(yy, self.piv, self.bot, gamma).astype(np.float32)

    @classmethod
    def for_sprite(cls, img, **kw):
        top, bot = silhouette_bbox(img)
        a = np.asarray(img)
        kw.setdefault("bot", a.shape[0] - 1 if bot >= a.shape[0] - 3 else bot)
        return cls(a.shape, top=top, **kw)

    @property
    def head_height(self):
        return float(self.piv - self.top)

    def __call__(self, img, dx, dy):
        """dx > 0 moves the head right, dy > 0 moves it down (pixels)."""
        a = np.asarray(img)
        if abs(dx) < 0.05 and abs(dy) < 0.05:
            return a.copy()
        mx = (self.xx - dx * self.w).astype(np.float32)
        my = (self.yy - dy * self.w).astype(np.float32)
        return cv2.remap(a, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
