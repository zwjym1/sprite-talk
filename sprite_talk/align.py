"""Optional Mandarin forced alignment with torchaudio's MMS_FA (needs torch,
torchaudio, pypinyin). Produces per-character [text, roman, start, end] rows."""
import json
import subprocess
import numpy as np


def align(audio_path, text):
    import torch
    import torchaudio
    from pypinyin import lazy_pinyin

    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False)
    dic = bundle.get_dict(star=None)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio_path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    w = torch.from_numpy(np.frombuffer(raw, np.int16).astype(np.float32) / 32768)[None]
    chars = [c for c in text if c.strip() and c not in "，。！？、,.!?;；:：\"'“”"]
    rom = [lazy_pinyin(c)[0].replace("ü", "u").replace("v", "u").lower() for c in chars]
    tok = [[dic[ch] for ch in r if ch in dic] for r in rom]
    keep = [i for i, t in enumerate(tok) if t]
    chars, rom, tok = [chars[i] for i in keep], [rom[i] for i in keep], [tok[i] for i in keep]
    with torch.inference_mode():
        em, _ = model(w)
    em = torch.log_softmax(em, -1)
    flat = torch.tensor([t for x in tok for t in x], dtype=torch.int32)[None]
    al, sc = torchaudio.functional.forced_align(em, flat, blank=0)
    spans = torchaudio.functional.merge_tokens(al[0], sc[0].exp())
    ratio = w.shape[1] / em.shape[1] / 16000
    out, k = [], 0
    for c, r, t in zip(chars, rom, tok):
        sp = spans[k:k + len(t)]
        k += len(t)
        out.append([c, r, round(sp[0].start * ratio, 3), round(sp[-1].end * ratio, 3)])
    return out


def main(audio, text, out):
    rows = align(audio, text)
    with open(out, "w") as f:
        json.dump(rows, f, ensure_ascii=False)
    print(f"aligned {len(rows)} chars -> {out}")
