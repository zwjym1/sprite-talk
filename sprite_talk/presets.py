"""Motion presets.

``aning_v4`` ports the talk motion of the approved host-A v4 render
(``science-studio/hosts/host_a/ai_talking/work/render_v4.py``) exactly, in
units of head height (hair top -> chin, 590 px on the host-A sprite):

* whole upper body is warped (not translated/rotated): weight 1 above a rigid
  line ``rigid_above_chin`` head-heights above the chin (host A: y=500, eye
  line), falling *linearly* to 0 at the pinned bottom;
* while speaking: ``theta = 2*pi*(t - onset)/T``, ``T = 12.5 f @30fps``
  ``dx = AX*g*(1-cos theta)/2``  (one-sided sway 0 -> +AX -> 0, period 12.5 f)
  ``dy = AY*g*|sin theta|``      (downward nod dips every 6.25 f)
  with AX = 17/590, AY = 33/590 head heights; phase restarts at each speech
  onset (when the gate has fallen below 0.02);
* gate g: one-pole follower of the speaking mask, attack k=0.45, release
  k=0.16; speaking mask = speech spans widened by -0.05 s / +0.30 s;
* idle breathing: ``dy -= 1.3/590 * (1-g) * (1-cos(2*pi*0.25 t))/2`` (rise).
No rotation, no scale.

``aning_feel`` is the *comfortable* Aning workflow profile (pose cuts + subtle
bottom-anchored body motion that moves without feeling shaky). Matched to
Skill SideTalk remeasure 2026-11-02 (median head dip ~19.5 px on ~390 px head
→ AY≈0.050 HH; sway ptp ~11.5 px → AX≈0.0295 HH):

* same bottom-anchored LinearPinWarp as v4;
* ``dy = AY*g*sin(theta)^2`` (C1-smooth raised-cosine family — no |sin| cusp);
* ``dx = AX*g*(1-cos(theta + lag))/2`` with ~70° phase lag (slanted ellipse);
* slower base loop ``T = 18 f @30fps`` (~0.60 s) — lower peak accel, closer to
  Aning's blunt turnaround (a_p95 ~4.5–6k) than the metronomic |sin| punch;
* **continuous global clock** (no onset phase reset) so pose cuts don't slam
  a fresh bounce corner;
* softer gate attack/release (0.22 / 0.12).

``aning_dyn`` keeps Aning's continuous SideTalk rate (~1 dip / 6f, sin² soft
turns) but adds speech-energy dynamics the equal-amp ``aning_feel`` lacked:

* same bottom-anchored LinearPinWarp + AX/AY HH units as feel;
* ``T = 12 f`` so sin² lobes peak every **6 f** (~5 dips/s while speaking);
* amplitude follows a smoothed RMS envelope: accents (syllable peaks) stronger,
  phrase tails softer; amp floor only while above ``energy_thr``;
* attack/release on the energy target so **pauses settle toward near-idle**
  (tiny breath only) — unlike feel's widened speaking-mask that held full amp
  through short gaps;
* continuous global clock, ~70° X lag, no onset reset.
"""
import math
import numpy as np
import cv2

ANING_V4 = dict(loop_frames=12.5, ref_fps=30, ax=17.0 / 590, ay=33.0 / 590, rigid_above_chin=181.0 / 590,
                breath=1.3 / 590, breath_hz=0.25, attack=0.45, release=0.16, lead_s=0.05, tail_s=0.30, onset_gate=0.02)

# Comfortable Aning workflow feel (not the punchy host-A v4 |sin| bob).
ANING_FEEL = dict(loop_frames=18.0, ref_fps=30, ax=0.0295, ay=0.0500, rigid_above_chin=181.0 / 590,
                  breath=1.0 / 590, breath_hz=0.22, attack=0.22, release=0.12, lead_s=0.05, tail_s=0.35,
                  onset_gate=0.02, x_phase_lag_deg=70.0, shape="sin2", continuous=True)

# Continuous Aning-rate dips + energy-driven amp + pause settle (user: 强弱/停顿收住).
ANING_DYN = dict(loop_frames=12.0, ref_fps=30, ax=0.0295, ay=0.0500, rigid_above_chin=181.0 / 590,
                 breath=1.2 / 590, breath_hz=0.22, attack=0.50, release=0.32,
                 energy_thr=0.07, amp_floor=0.62, amp_gamma=1.0, peak_boost=0.10,
                 x_phase_lag_deg=70.0, shape="sin2", continuous=True, energy_driven=True)

PRESETS = {"aning_v4": ANING_V4, "aning_feel": ANING_FEEL, "aning_dyn": ANING_DYN}


def speaking_mask(talking, fps, lead_s, tail_s):
    t = np.asarray(talking, bool); n = len(t); out = np.zeros(n, bool)
    a, b = int(round(lead_s * fps)), int(round(tail_s * fps))
    for i in np.flatnonzero(t):
        out[max(0, i - a):min(n, i + b + 1)] = True
    return out


def aning_v4_series(n, head_px, talking, fps=30, p=ANING_V4, amp=1.0):
    """Return (dx, dy, gate) in pixels at the head for ``n`` frames (dy>0 = down)."""
    spk = speaking_mask(talking, fps, p["lead_s"], p["tail_s"]).astype(float)
    T = p["loop_frames"] / p["ref_fps"]
    g = np.zeros(n); dx = np.zeros(n); dy = np.zeros(n); t_on = 0.0
    for i in range(n):
        prev = g[i - 1] if i else 0.0
        if spk[i] and prev < p["onset_gate"]:
            t_on = i / fps
        g[i] = prev + (spk[i] - prev) * (p["attack"] if spk[i] else p["release"])
        t = i / fps; th = 2 * math.pi * (t - t_on) / T
        breath = -p["breath"] * (0.5 - 0.5 * math.cos(2 * math.pi * p["breath_hz"] * t))
        dx[i] = p["ax"] * g[i] * (1 - math.cos(th)) / 2
        dy[i] = p["ay"] * g[i] * abs(math.sin(th)) + breath * (1 - g[i])
    s = head_px * amp
    return dx * s, dy * s, g


def aning_feel_series(n, head_px, talking, fps=30, p=ANING_FEEL, amp=1.0):
    """Comfortable Aning-matched series: sin² dips, slower loop, continuous clock."""
    spk = speaking_mask(talking, fps, p["lead_s"], p["tail_s"]).astype(float)
    T = p["loop_frames"] / p["ref_fps"]
    lag = math.radians(p.get("x_phase_lag_deg", 0.0))
    g = np.zeros(n); dx = np.zeros(n); dy = np.zeros(n)
    for i in range(n):
        prev = g[i - 1] if i else 0.0
        g[i] = prev + (spk[i] - prev) * (p["attack"] if spk[i] else p["release"])
        t = i / fps
        th = 2 * math.pi * t / T  # continuous — never reset on onset
        breath = -p["breath"] * (0.5 - 0.5 * math.cos(2 * math.pi * p["breath_hz"] * t))
        # sin² = (1-cos(2θ))/2 — C1 at zeros (no rubber-band cusp)
        dy[i] = p["ay"] * g[i] * (math.sin(th) ** 2) + breath * (1 - g[i])
        dx[i] = p["ax"] * g[i] * (1 - math.cos(th + lag)) / 2
    s = head_px * amp
    return dx * s, dy * s, g


def aning_dyn_series(n, head_px, talking, fps=30, p=ANING_DYN, amp=1.0, env=None):
    """Continuous Aning-rate sin² dips with energy-driven amplitude + pause settle.

    ``env``: optional per-frame mouth/RMS envelope in ~[0,1]. When omitted, a flat
    proxy is built from the boolean ``talking`` mask (loses 强弱 dynamics).
    """
    if env is None:
        env = np.asarray(talking, float)
    else:
        env = np.asarray(env, float)
    if len(env) < n:
        env = np.r_[env, np.zeros(n - len(env))]
    env = env[:n]
    thr = float(p.get("energy_thr", 0.07))
    floor = float(p.get("amp_floor", 0.62))
    gamma = float(p.get("amp_gamma", 1.0))
    peak_boost = float(p.get("peak_boost", 0.10))
    # light smooth
    e = np.convolve(env, np.array([0.25, 0.5, 0.25]), mode="same")
    speak = e >= thr
    hi = float(np.percentile(e[speak], 92)) if speak.any() else 0.5
    # syllable / accent peaks in energy
    accent = np.zeros(n)
    for i in range(1, n - 1):
        if e[i] >= e[i - 1] and e[i] > e[i + 1] and e[i] >= thr + 0.02:
            # prominence vs neighbors
            prom = e[i] - 0.5 * (e[i - 1] + e[i + 1])
            if prom >= 0.015:
                for d, w in ((-1, 0.45), (0, 1.0), (1, 0.45)):
                    j = i + d
                    if 0 <= j < n:
                        accent[j] = max(accent[j], w)
    raw = np.zeros(n)
    for i in range(n):
        if e[i] < thr:
            raw[i] = 0.0
        else:
            u = min(1.0, max(0.0, (e[i] - thr) / max(1e-6, hi - thr)))
            a = floor + (1.0 - floor) * (u ** gamma)
            raw[i] = min(1.15, a * (1.0 + peak_boost * accent[i]))
    g = np.zeros(n)
    dx = np.zeros(n)
    dy = np.zeros(n)
    lag = math.radians(p.get("x_phase_lag_deg", 0.0))
    T = p["loop_frames"] / p["ref_fps"]
    for i in range(n):
        prev = g[i - 1] if i else 0.0
        tgt = raw[i]
        g[i] = prev + (tgt - prev) * (p["attack"] if tgt > prev else p["release"])
        t = i / fps
        th = 2 * math.pi * t / T  # continuous clock
        breath = -p["breath"] * (0.5 - 0.5 * math.cos(2 * math.pi * p["breath_hz"] * t))
        bob = g[i]
        settle = 1.0 - min(1.0, bob / 0.20)
        dy[i] = p["ay"] * bob * (math.sin(th) ** 2) + breath * settle
        dx[i] = p["ax"] * bob * (1 - math.cos(th + lag)) / 2
    s = head_px * amp
    return dx * s, dy * s, g


def series_for_preset(name, n, head_px, talking, fps=30, amp=1.0, env=None):
    if name == "aning_v4":
        return aning_v4_series(n, head_px, talking, fps, ANING_V4, amp)
    if name == "aning_feel":
        return aning_feel_series(n, head_px, talking, fps, ANING_FEEL, amp)
    if name == "aning_dyn":
        return aning_dyn_series(n, head_px, talking, fps, ANING_DYN, amp, env=env)
    raise KeyError(name)


class LinearPinWarp:
    """Host-A v4 warp: rigid above ``rigid_y``, linear falloff to 0 at ``pin_y``."""

    def __init__(self, shape, rigid_y, pin_y):
        h, w = shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.w = np.clip((pin_y - yy) / max(1.0, pin_y - rigid_y), 0, 1).astype(np.float32)
        self.rigid_y, self.pin_y = rigid_y, pin_y

    def __call__(self, img, dx, dy):
        a = np.asarray(img)
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return a.copy()
        dx, dy = np.float32(dx), np.float32(dy)
        return cv2.remap(a, self.xx - dx * self.w, self.yy - dy * self.w, cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
