# menorah.py

import uasyncio as asyncio


class MenorahController:
    """
    High-level controller for the menorah candles.

    - candles: list[ Candle ] with .on() / .off()
    - shamash_index: index in the candles list for the shamash (default 0).
    - state:
        -1  = outside Hanukkah (default pattern)
         0  = Hanukkah daytime, candles OFF
        1-8 = Hanukkah night N, candles ON
    """

    def __init__(self, candles, shamash_index=0):
        self._candles = list(candles)
        if not self._candles:
            raise ValueError("MenorahController requires at least one candle")

        self._shamash_index = shamash_index

        # Use a concrete int, not None, to keep type checkers happy
        self._state: int = -1
        self._last_state: int = -2  # "impossible" value so first apply always runs

    # ---- public API -----------------------------------------------------

    def set_state(self, state: int) -> None:
        """Called by ModeManager with -1, 0, or 1..8."""
        self._state = state

    # ---- internals ------------------------------------------------------

    def _all_off(self) -> None:
        for c in self._candles:
            c.off()

    def _all_on(self) -> None:
        for c in self._candles:
            c.on()

    def _apply_hanukkah_lit(self, night: int) -> None:
        total = len(self._candles)
        if total == 0:
            return

        # Clamp night to 1..8
        if night < 1:
            night = 1
        if night > 8:
            night = 8

        self._all_off()

        # Shamash always on
        if 0 <= self._shamash_index < total:
            self._candles[self._shamash_index].on()

        # Side candles: all except shamash, left→right
        side_indices = [i for i in range(total) if i != self._shamash_index]
        side_indices.sort()

        for idx in side_indices[:night]:
            self._candles[idx].on()

    def _apply_state(self, state: int) -> None:
        """
        Apply the hardware pattern for the given state.
        """
        if state < 0:
            # Outside Hanukkah: placeholder "default" behavior.
            self._all_on()
        elif state == 0:
            # Hanukkah daytime: all off.
            self._all_off()
        else:
            # 1..8 = Hanukkah night N
            self._apply_hanukkah_lit(state)

    async def run(self, poll_ms: int = 100) -> None:
        """
        Periodically apply state when it changes.
        """
        while True:
            if self._state != self._last_state:
                self._apply_state(self._state)
                self._last_state = self._state
            await asyncio.sleep_ms(poll_ms)
