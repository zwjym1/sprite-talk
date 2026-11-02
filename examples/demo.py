#!/usr/bin/env python3
"""Render the Host A example and self-check it.

    python examples/demo.py [--out out/host_a_demo.mp4]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sprite_talk.render import render  # noqa: E402
from sprite_talk.sync import measure  # noqa: E402
from sprite_talk.calibrate import read_frames, fit  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "out", "host_a_demo.mp4"))
ap.add_argument("--skip-calibrate", action="store_true")
a = ap.parse_args()
os.makedirs(os.path.dirname(a.out), exist_ok=True)
H = os.path.join(HERE, "host_a")
info = render(os.path.join(H, "sprites.json"), os.path.join(H, "vo.mp3"), a.out,
              alignment=os.path.join(H, "vo_timings.json"))
print("render:", json.dumps(info))
print("sync:", json.dumps(measure(a.out, (420, 560, 560, 700))))
if not a.skip_calibrate:
    # round trip: calibrate on our own render; a clean warp should give dy gain ~1.0
    fr, fps = read_frames(a.out, 0.0, 4.0)
    curve, rep = fit(fr[:, :, :], one_loop=False)
    print("calibrate (self round-trip):", json.dumps(rep))
print("wrote", a.out)
