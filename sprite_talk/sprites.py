"""Sprite set: a base image plus mouth / eye overlays.

Overlays may be full-size images or crops placed at an offset. Only the pixels
that differ from the base (inside an ROI) are pasted, with a feathered mask and
low-frequency colour correction, so generated overlays blend into the base.
Config (JSON):
{
  "base": "base.png",
  "overlay_offset": [x, y],              # where crop overlays sit on the base
  "mouth_roi": [x0, y0, x1, y1], "eye_roi": [x0, y0, x1, y1],
  "mouth": {"closed": "m_closed.png", "small": "m_E.png", "large": "m_A.png"},
  "eyes":  {"half": "e_half.png", "closed": "e_closed.png"}
}
Mouth keys may also be viseme names (A E I O U N MBP F) for viseme mode.
"""
import json
import os
import numpy as np
import cv2
from PIL import Image


class SpriteSet:
    def __init__(self, cfg_path):
        with open(cfg_path) as f:
            cfg = json.load(f)
        root = os.path.dirname(os.path.abspath(cfg_path))
        p = lambda n: os.path.join(root, n)
        self.base = np.array(Image.open(p(cfg["base"])).convert("RGBA"))
        self.H, self.W = self.base.shape[:2]
        self.off = tuple(cfg.get("overlay_offset", [0, 0]))
        self.cfg = cfg
        self.mouth = {k: self._patch(p(v), cfg["mouth_roi"]) for k, v in cfg.get("mouth", {}).items()}
        self.eyes = {k: self._patch(p(v), cfg["eye_roi"], thr=16, grow=3) for k, v in cfg.get("eyes", {}).items()}

    def _full(self, path):
        g = np.array(Image.open(path).convert("RGB")).astype(np.float32)
        if g.shape[:2] == (self.H, self.W):
            return g
        full = self.base[..., :3].astype(np.float32).copy()
        x, y = self.off
        full[y:y + g.shape[0], x:x + g.shape[1]] = g
        return full

    def _patch(self, path, roi, thr=14, grow=4, feather=2.0):
        g = self._full(path)
        b = self.base[..., :3].astype(np.float32)
        x0, y0, x1, y1 = roi
        d = np.abs(g - b).max(2)
        m = np.zeros((self.H, self.W), np.uint8)
        m[y0:y1, x0:x1] = d[y0:y1, x0:x1] > thr
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=grow)
        w = ((d < thr) & (m == 0)).astype(np.float32)
        num = cv2.GaussianBlur((g - b) * w[..., None], (0, 0), 10)
        den = cv2.GaussianBlur(w, (0, 0), 10)[..., None] + 1e-3
        g = g - num / den
        a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), feather)
        r = np.zeros((self.H, self.W), np.float32)
        r[y0:y1, x0:x1] = 1
        a = a * cv2.GaussianBlur(r, (0, 0), 3)
        return np.clip(g, 0, 255), a[..., None]

    @staticmethod
    def _apply(img, patch):
        g, a = patch
        img[..., :3] = (g * a + img[..., :3] * (1 - a)).astype(np.uint8)

    def frame(self, mouth="closed", eyes=None):
        img = self.base.copy()
        if mouth in self.mouth:
            self._apply(img, self.mouth[mouth])
        if eyes in self.eyes:
            self._apply(img, self.eyes[eyes])
        return img
