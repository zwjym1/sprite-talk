"""Fit a talk-loop motion curve against a reference clip you supply.

Pipeline (one still -> every frame):
 1. Read frames of the clip (optionally cropped / time-ranged).
 2. Silhouette = max(RGB) > thr on a dark/plain background (or --bg-diff).
 3. Dense optical flow (Farneback) from every frame back to a reference still.
 4. Least-squares fit of flow = w(y) * (dx, dy) with the bottom-anchored falloff
    w(y) over the silhouette -> per-frame dx, dy (in pixels).
 5. Silhouette-top "dip" per frame (how far the head top drops).
 6. Gain search: re-render the still with the warp at dy = g * dip for a grid of
    g and keep the g with the lowest pixel error vs the real frames (0.75 in our
    reference). The raw flow/dip slope is reported too, but flow under-reads on
    flat-colour regions, so the render-and-compare gain is the one to use.
 7. Optional: detect the loop period by autocorrelation and keep one period.
Outputs a curve JSON (head-height units, dy in dip units) for --curve.
"""
import json
import subprocess
import numpy as np
import cv2
from .warp import falloff_weight


def read_frames(path, start=0.0, dur=None, crop=None):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    W, H = int(probe[0]), int(probe[1])
    num, den = probe[2].split("/")
    fps = float(num) / float(den)
    vf = []
    if crop:
        x0, y0, x1, y1 = crop
        vf = ["-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"]
        W, H = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", str(path)] + (["-t", str(dur)] if dur else [])
    cmd += vf + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3), fps


def silhouette(frames, thr=45, bg_diff=False):
    if bg_diff:
        bg = np.median(frames, 0)
        return np.abs(frames.astype(int) - bg).max(-1) > thr
    return frames.max(-1) > thr


def loop_period(sig, lo=8, hi=None):
    s = sig - sig.mean()
    hi = hi or len(s) // 2
    ac = [np.dot(s[:-k], s[k:]) / (len(s) - k) for k in range(lo, hi)]
    return lo + int(np.argmax(ac)) if ac else len(s)


def fit(frames, still=None, thr=45, bg_diff=False, piv_ratio=0.355, gamma=1.0, step=4, head_px=None, one_loop=True):
    N, H, W = frames.shape[:3]
    masks = silhouette(frames, thr, bg_diff)
    tops = np.array([np.where(m.any(1))[0].min() if m.any() else -1 for m in masks], float)
    good = tops >= 0
    tops[~good] = np.median(tops[good])
    if still is None:  # median-height frame
        still = int(np.argsort(tops)[N // 2])
    m0 = masks[still]
    rows = np.where(m0.any(1))[0]
    top, bot = rows.min(), rows.max()
    if bot >= H - 3:
        bot = H - 1
    piv = top + piv_ratio * (bot - top)
    head_px = head_px or (piv - top)
    g0 = cv2.cvtColor(frames[still], cv2.COLOR_RGB2GRAY)
    yy, xx = np.mgrid[0:H:step, 0:W:step]
    sel = m0[::step, ::step]
    w = falloff_weight(yy[sel].astype(float), piv, bot, gamma)
    A = np.zeros((2 * len(w), 2))
    A[:len(w), 0] = w
    A[len(w):, 1] = w
    P = []
    for f in frames:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        fl = cv2.calcOpticalFlowFarneback(g0, g, None, 0.5, 4, 21, 3, 5, 1.1, 0)
        # flow at still pixel p points to where it is in frame f -> displacement of content
        u, v = fl[::step, ::step, 0][sel], fl[::step, ::step, 1][sel]
        p, *_ = np.linalg.lstsq(A, np.r_[u, v], rcond=None)
        P.append(p)
    P = np.array(P)
    dx = P[:, 0] - np.median(P[:, 0])
    dy_flow = P[:, 1] - P[:, 1].min()
    dip = tops - tops.min()
    gain = float(np.dot(dy_flow - dy_flow.mean(), dip - dip.mean()) / (np.dot(dip - dip.mean(), dip - dip.mean()) + 1e-9))
    corr = float(np.corrcoef(dy_flow, dip)[0, 1]) if dip.std() > 0 else 0.0
    # render-and-compare gain search (half resolution)
    sm = lambda im: cv2.resize(im, (W // 2, H // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
    st = sm(frames[still])
    ys, xs = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)
    wf = falloff_weight(ys, piv / 2, bot / 2, gamma).astype(np.float32)
    sub = range(0, N, max(1, N // 60))
    real = [sm(frames[i]) for i in sub]
    def err(gx, gy):
        e = 0.0
        for k, i in enumerate(sub):
            ddx, ddy = np.float32(gx * dx[i] / 2), np.float32(gy * (dip[i] - dip[still]) / 2)
            r = cv2.remap(st, xs - ddx * wf, ys - ddy * wf, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            e += np.abs(r - real[k]).mean()
        return e / len(real)
    gy_grid = np.round(np.arange(0.4, 1.31, 0.05), 2)
    errs = {float(g): err(1.0, g) for g in gy_grid}
    g_best = min(errs, key=errs.get)
    gx_errs = {float(g): err(g, g_best) for g in (0.8, 0.9, 1.0, 1.1, 1.2)}
    gx_best = min(gx_errs, key=gx_errs.get)
    period = loop_period(dip) if one_loop and N >= 20 else N
    sl = slice(0, period)
    rest = dip[sl].min()
    curve = {
        "units": "head_height",
        "dx": [round(float(v) * gx_best / head_px, 4) for v in dx[sl]],
        "dy": [round(float(v - rest) / head_px, 4) for v in dip[sl]],
    }
    report = dict(frames=int(N), still=int(still), head_px=round(float(head_px), 1), piv=round(float(piv), 1),
                  bot=int(bot), loop_frames=int(period), dx_ptp_px=round(float(np.ptp(dx)), 2),
                  dip_ptp_px=round(float(np.ptp(dip)), 2), flow_dy_ptp_px=round(float(np.ptp(dy_flow)), 2),
                  recommended_dy_gain=g_best, dx_gain_applied=gx_best,
                  mae_at_gain={str(k): round(float(v), 3) for k, v in errs.items()},
                  flow_dip_slope=round(gain, 3), flow_vs_dip_corr=round(corr, 3))
    return curve, report


def main(clip, out, start=0.0, dur=None, crop=None, still=None, thr=45, bg_diff=False, piv_ratio=0.355,
         head_px=None, one_loop=True):
    frames, fps = read_frames(clip, start, dur, crop)
    curve, rep = fit(frames, still, thr, bg_diff, piv_ratio, head_px=head_px, one_loop=one_loop)
    curve["fps"] = round(fps, 3)
    curve["calibration"] = rep
    with open(out, "w") as f:
        json.dump(curve, f, indent=1)
    print(json.dumps(rep, indent=1))
    print("curve ->", out, "| use with --curve and --dy-gain", rep["recommended_dy_gain"])
