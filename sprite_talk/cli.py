import argparse
import json


def _box(s):
    return tuple(int(v) for v in s.split(","))


def main(argv=None):
    ap = argparse.ArgumentParser("sprite-talk", description="2D sprite talking-head toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render mp4 from sprites.json + audio")
    r.add_argument("sprites"); r.add_argument("audio"); r.add_argument("-o", "--out", default="talk.mp4")
    r.add_argument("--fps", type=int, default=30); r.add_argument("--curve")
    r.add_argument("--amp", type=float, default=1.0); r.add_argument("--dy-gain", type=float, default=0.75)
    r.add_argument("--piv-ratio", type=float, default=0.355); r.add_argument("--alignment")
    r.add_argument("--visemes", action="store_true"); r.add_argument("--seed", type=int, default=0)
    r.add_argument("--dur", type=float); r.add_argument("--bg", default="0,0,0")
    r.add_argument("--preset", choices=["aning_v4", "aning_feel", "aning_dyn"], help="motion preset (overrides --curve/--dy-gain/--piv-ratio)")
    r.add_argument("--head-px", type=float, help="head height hair-top->chin (px) for --preset")
    r.add_argument("--chin-y", type=float, help="chin row (px) for --preset")

    m = sub.add_parser("mouth", help="print per-frame mouth levels")
    m.add_argument("audio"); m.add_argument("--alignment"); m.add_argument("--fps", type=int, default=30)
    m.add_argument("-o", "--out")

    b = sub.add_parser("blinks", help="print blink schedule")
    b.add_argument("frames", type=int); b.add_argument("--fps", type=int, default=30); b.add_argument("--seed", type=int, default=0)

    s = sub.add_parser("sync", help="measure lip sync of a rendered video")
    s.add_argument("video"); s.add_argument("--box", type=_box, required=True, help="x0,y0,x1,y1 around the mouth")
    s.add_argument("--mode", choices=["dark", "red"], default="dark"); s.add_argument("--thr", type=int, default=90)
    s.add_argument("--dur", type=float)

    c = sub.add_parser("calibrate", help="fit a motion curve from a reference clip")
    c.add_argument("clip"); c.add_argument("-o", "--out", default="curve.json")
    c.add_argument("--start", type=float, default=0.0); c.add_argument("--dur", type=float)
    c.add_argument("--crop", type=_box); c.add_argument("--still", type=int)
    c.add_argument("--thr", type=int, default=45); c.add_argument("--bg-diff", action="store_true")
    c.add_argument("--piv-ratio", type=float, default=0.355); c.add_argument("--head-px", type=float)
    c.add_argument("--full", action="store_true", help="keep all frames instead of one detected loop")

    a = sub.add_parser("align", help="Mandarin forced alignment (torchaudio MMS_FA)")
    a.add_argument("audio"); a.add_argument("text"); a.add_argument("-o", "--out", default="alignment.json")

    x = ap.parse_args(argv)
    if x.cmd == "render":
        from .render import render
        print(json.dumps(render(x.sprites, x.audio, x.out, x.fps, x.curve, x.amp, x.dy_gain, x.piv_ratio,
                                x.alignment, x.visemes, _box(x.bg), x.seed, x.dur,
                                preset=x.preset, head_px=x.head_px, chin_y=x.chin_y)))
    elif x.cmd == "mouth":
        from .mouth import audio_rms, audio_duration, mouth_levels, load_alignment
        n = int(round(audio_duration(x.audio) * x.fps))
        lvl, _ = mouth_levels(audio_rms(x.audio, x.fps), n, x.fps, load_alignment(x.alignment) if x.alignment else None)
        s_ = "".join(map(str, lvl.tolist()))
        open(x.out, "w").write(s_) if x.out else print(s_)
    elif x.cmd == "blinks":
        from .blink import blink_schedule
        print(json.dumps(blink_schedule(x.frames, x.fps, seed=x.seed)))
    elif x.cmd == "sync":
        from .sync import measure
        print(json.dumps(measure(x.video, x.box, dur=x.dur, mode=x.mode, thr=x.thr)))
    elif x.cmd == "calibrate":
        from .calibrate import main as cal
        cal(x.clip, x.out, x.start, x.dur, x.crop, x.still, x.thr, x.bg_diff, x.piv_ratio, x.head_px, not x.full)
    elif x.cmd == "align":
        from .align import main as al
        al(x.audio, x.text, x.out)


if __name__ == "__main__":
    main()
