# menorah.py

import uasyncio as asyncio
from mode_manager import MODE_HANUKKAH_LIT, MODE_HANUKKAH_DARK, MODE_DEFAULT


class MenorahController:
    """
    High-level controller for the menorah candles.

    - candles: list[ Candle ] (must support .on() and .off()).
    - shamash_index: index in the candles list for the shamash.
      If None, defaults to the center candle.
    """

    def __init__(self, candles, shamash_index=None):
        self._candles = list(candles)
        if not self._candles:
            raise ValueError("MenorahController requires at least one candle")

        if shamash_index is None:
            shamash_index = len(self._candles) // 2
        self._shamash_index = shamash_index

        self._mode = MODE_DEFAULT
        self._night = None

        self._last_mode = None
        self._last_night = None

    def set_mode(self, mode, night=None):
        """Called by ModeManager."""
        self._mode = mode
        self._night = night

    def _all_off(self):
        for c in self._candles:
            c.off()

    def _all_on(self):
        for c in self._candles:
            c.on()

    def _apply_hanukkah_lit(self, night):
        total = len(self._candles)
        if total == 0:
            return

        # Clamp night to 1..8
        if night is None or night < 1:
            night = 1
        if night > 8:
            night = 8

        self._all_off()

        # Shamash always on
        if 0 <= self._shamash_index < total:
            self._candles[self._shamash_index].on()

        # Side candles: all except shamash, sorted left→right
        side_indices = [i for i in range(total) if i != self._shamash_index]
        side_indices.sort()

        for idx in side_indices[:night]:
            self._candles[idx].on()

    def _apply_state(self, mode, night):
        if mode == MODE_HANUKKAH_LIT:
            self._apply_hanukkah_lit(night)
        elif mode == MODE_HANUKKAH_DARK:
            self._all_off()
        elif mode == MODE_DEFAULT:
            # Outside Hanukkah: for now, all on (placeholder for future binary clock).
            self._all_on()
        else:
            self._all_off()

    async def run(self, poll_ms=100):
        """
        Periodically apply state if mode/night changed.
        Individual Candle objects can still implement flicker internally.
        """
        while True:
            if (self._mode != self._last_mode) or (self._night != self._last_night):
                self._apply_state(self._mode, self._night)
                self._last_mode = self._mode
                self._last_night = self._night

            await asyncio.sleep_ms(poll_ms)
