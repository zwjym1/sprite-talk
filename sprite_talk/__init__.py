"""sprite-talk: 2D sprite talking-head animation (body warp, mouth track, blinks)."""
__version__ = "0.1.0"
from .warp import BodyWarp, falloff_weight
from .curves import GENERIC_LOOP, bob_series
from .mouth import audio_rms, mouth_levels, load_alignment
from .blink import blink_schedule
