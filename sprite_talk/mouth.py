"""Mouth track: loudness -> closed(0)/small(1)/large(2), consonant closures,
flicker removal. Optional viseme sequence from a char/word alignment."""
import json
import subprocess
import numpy as np

VOWELS = set("aeiouv")


def decode_audio(path, sr=16000, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def audio_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def audio_rms(path, fps=30, dur=None, sr=16000):
    """Per-frame RMS, normalised to max 1."""
    a = decode_audio(path, sr, dur)
    h = sr // fps
    n = len(a) // h
    r = np.sqrt((a[: n * h].reshape(n, h) ** 2).mean(1))
    return r / (r.max() + 1e-9)


def _roman(text):
    try:
        from pypinyin import lazy_pinyin
        return lazy_pinyin(text)[0].lower()
    except Exception:
        return text.lower()


def load_alignment(path):
    """Alignment JSON: list of {"text","start","end"} (seconds) or
    [text, roman, start, end, ...] rows (output of ``sprite-talk align``)."""
    with open(path) as f:
        d = json.load(f)
    out = []
    for r in d:
        if isinstance(r, dict):
            out.append((r["text"], r.get("roman") or _roman(r["text"]), float(r["start"]), float(r["end"])))
        else:
            out.append((r[0], r[1], float(r[2]), float(r[3])))
    return out


def mouth_levels(rms, n, fps=30, align=None, lead=0.033, hi=0.42, lo=0.13):
    """Return (levels[n] in {0,1,2}, smoothed envelope).

    lead: mouth leads audio by ~1 frame (reads as better sync).
    align: optional [(text, roman, start, end)]; a closed frame is forced at the
           onset of every syllable starting with a consonant -> per-syllable flap.
    """
    r = np.r_[rms, np.zeros(max(0, n + 2 - len(rms)))][: n + 2]
    e = np.convolve(r, [0.25, 0.5, 0.25], "same")
    sh = int(round(lead * fps))
    e = np.r_[e[sh:], np.zeros(sh)][:n]
    lvl = np.where(e > hi, 2, np.where(e > lo, 1, 0))
    for text, rom, s, _ in align or []:
        f = int(round(s * fps)) - sh
        if 0 < f < n and rom[:1] and rom[:1] not in VOWELS:
            lvl[f] = 0
    # remove isolated 1-frame open blips (closures of >=1 frame are kept)
    for f in range(1, n - 1):
        if lvl[f] > 0 and lvl[f - 1] == 0 and lvl[f + 1] == 0:
            lvl[f] = 0
    return lvl, e


# ---- optional visemes (Mandarin pinyin finals -> mouth shapes)
def _vis(text):
    from pypinyin import pinyin, Style
    ini = pinyin(text, style=Style.INITIALS, strict=False)[0][0]
    f = pinyin(text, style=Style.FINALS, strict=False)[0][0].replace("v", "u")
    table = [
        (lambda: ini in ("z", "c", "s", "zh", "ch", "sh", "r") and f == "i", ["E"]),
        (lambda: f in ("ai", "uai"), ["A", "I"]), (lambda: f in ("ao", "iao"), ["A", "O"]),
        (lambda: f in ("ou", "iou", "iu"), ["O", "U"]), (lambda: f == "ei", ["E", "I"]),
        (lambda: f in ("uei", "ui"), ["U", "I"]), (lambda: f in ("ian", "ie", "ue"), ["I", "E"]),
        (lambda: f in ("a", "ua", "ia"), ["A"]), (lambda: f in ("uan", "iang", "uang", "an", "ang"), ["A", "N"]),
        (lambda: f in ("o", "uo"), ["O"]), (lambda: f in ("ong", "iong"), ["O", "U"]),
        (lambda: f in ("e", "er"), ["E"]), (lambda: f in ("en", "eng"), ["E", "N"]),
        (lambda: f in ("un", "uen"), ["U", "N"]), (lambda: f in ("i", "in", "ing"), ["I"]), (lambda: f == "u", ["U"]),
    ]
    for cond, seq in table:
        if cond():
            return ini, seq
    return ini, ["E"]


def viseme_track(align, n, fps=30, lead=0.03):
    """Per-frame viseme labels: X (rest), MBP, F, A, E, I, O, U, N. Needs pypinyin.
    Non-CJK tokens fall back to 'E'."""
    seq = ["X"] * n
    fr = lambda t: int(round((t - lead) * fps))
    for i, (text, rom, s, e) in enumerate(align):
        nxt = align[i + 1][2] if i + 1 < len(align) else 1e9
        e2 = nxt if nxt - e < 0.16 else e + 0.07
        try:
            ini, v = _vis(text[:1])
        except Exception:
            ini, v = "", ["E"]
        a, c = fr(s), fr(e2)
        b = a
        if ini in ("b", "p", "m", "f"):
            b = a + 2
            for f in range(max(0, a), min(n, b)):
                seq[f] = "F" if ini == "f" else "MBP"
        L = max(1, c - b)
        for f in range(max(0, b), min(n, c)):
            seq[f] = v[min(len(v) - 1, (f - b) * len(v) // L)]
    return seq
