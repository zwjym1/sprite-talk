"""Blink scheduler -> {frame: eye_state} with 1 = half, 2 = closed."""
import random


def blink_schedule(n, fps=30, mean_gap=3.8, jitter=1.4, double_p=0.15, seed=0, first=1.2):
    rnd = random.Random(seed)
    out = {}
    t = first + rnd.uniform(0, jitter)
    while True:
        f = int(t * fps)
        if f + 4 >= n:
            break
        pattern = [1, 2, 2, 1]
        if rnd.random() < double_p:
            pattern += [0, 1, 2, 1]
        for i, s in enumerate(pattern):
            if s:
                out[f + i] = s
        t += max(1.5, rnd.gauss(mean_gap, jitter))
    return out
