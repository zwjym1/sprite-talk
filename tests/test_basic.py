import numpy as np
from sprite_talk import BodyWarp, falloff_weight, bob_series, mouth_levels, blink_schedule


def test_weight():
    w = falloff_weight(np.array([0, 50, 75, 100, 120.0]), 50, 100)
    assert list(w) == [1, 1, 0.5, 0, 0]


def test_warp_pins_bottom():
    img = np.zeros((100, 40, 3), np.uint8); img[10:20] = 255
    W = BodyWarp(img.shape, top=10, bot=99, piv=40)
    out = W(img, 0, 5)
    assert out[15:25].mean() > 200 and (out[-1] == img[-1]).all()


def test_bob_scales_with_head():
    a = bob_series(50, 100); b = bob_series(50, 200)
    assert np.allclose(b[1], 2 * a[1])


def test_mouth_flicker():
    r = np.array([0, 0, 0.5, 0, 0, 0.9, 0.9, 0.9, 0, 0] * 3, float)
    lvl, _ = mouth_levels(r, 30, lead=0)
    for f in range(1, 29):
        assert not (lvl[f] > 0 and lvl[f - 1] == 0 and lvl[f + 1] == 0)


def test_blinks():
    b = blink_schedule(600, seed=1)
    assert b and set(b.values()) <= {1, 2}
