# menorah.py

import uasyncio as asyncio
import time


class MenorahController:
    """
    High-level controller for the menorah candles.

    - candles: list[ Candle ] with .on() / .off()
    - shamash_index: index in the candles list for the shamash (default 0).
    - state:
        -1  = outside Hanukkah (chaser pattern)
         0  = Hanukkah daytime, candles OFF
        1-8 = Hanukkah night N, candles ON
    """

    def __init__(self, candles, shamash_index=0):
        self._candles = list(candles)
        if not self._candles:
            raise ValueError("MenorahController requires at least one candle")

        self._shamash_index = shamash_index

        # Always-int to keep type checkers happy
        self._state: int = -1
        self._last_state: int = -2  # "impossible" so first apply always runs

        # For chaser mode (state = -1)
        self._chaser_index: int = 0
        self._chaser_last_ms: int = time.ticks_ms()
        self._chaser_period_ms: int = 5000  # 5 seconds per candle

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_state(self, state: int) -> None:
        """Called by ModeManager with -1, 0, or 1..8."""
        self._state = state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_off(self) -> None:
        for c in self._candles:
            c.off()

    def _all_on(self) -> None:
        for c in self._candles:
            c.on()

    def _side_indices(self):
        total = len(self._candles)
        return sorted(i for i in range(total) if i != self._shamash_index)

    def _apply_hanukkah_lit(self, night: int) -> None:
        """
        Shamash + N side candles ON.
        """
        total = len(self._candles)
        if total == 0:
            return

        # Clamp night
        if night < 1:
            night = 1
        if night > 8:
            night = 8

        side_indices = self._side_indices()
        if not side_indices:
            return

        if night > len(side_indices):
            night = len(side_indices)

        self._all_off()

        # Shamash ON
        if 0 <= self._shamash_index < total:
            self._candles[self._shamash_index].on()

        # First N side candles ON
        for idx in side_indices[:night]:
            self._candles[idx].on()

    def _apply_state_static(self, state: int) -> None:
        """
        Apply NON-chaser states (0 or 1..8).

        state < 0 should not come here (handled in run()).
        """
        if state == 0:
            # Hanukkah daytime: all off.
            self._all_off()
        else:
            # 1..8 = Hanukkah night N
            self._apply_hanukkah_lit(state)

    # ------------------ chaser (-1) helpers ----------------------------

    def _reset_chaser(self) -> None:
        """
        Called when we enter state -1 to reset the animation.
        """
        self._chaser_index = 0
        self._chaser_last_ms = time.ticks_ms()
        self._apply_chaser_step()

    def _apply_chaser_step(self) -> None:
        """
        Turn shamash ON and exactly one side candle ON, all others OFF.
        """
        total = len(self._candles)
        if total <= 1:
            return

        side_indices = self._side_indices()
        if not side_indices:
            return

        # Wrap index into range
        idx = self._chaser_index % len(side_indices)

        # Clear all, then shamash + one side
        self._all_off()

        if 0 <= self._shamash_index < total:
            self._candles[self._shamash_index].on()

        self._candles[side_indices[idx]].on()

    def _tick_chaser_if_due(self) -> None:
        """
        Advance the chaser if 5 seconds have passed since the last step.
        """
        now = time.ticks_ms()
        if time.ticks_diff(now, self._chaser_last_ms) >= self._chaser_period_ms:
            self._chaser_index += 1  # next candle
            self._chaser_last_ms = now
            self._apply_chaser_step()

    # ------------------------------------------------------------------
    # Task
    # ------------------------------------------------------------------

    async def run(self, poll_ms: int = 100) -> None:
        """
        Periodically apply either:

        - chaser pattern when state == -1, or
        - static Hanukkah pattern when state >= 0.

        The chaser stops immediately when state changes to >= 0.
        """
        while True:
            if self._state == -1:
                # Just entered -1? reset the chaser.
                if self._last_state != -1:
                    self._reset_chaser()
                    self._last_state = -1

                # Advance chaser if needed.
                self._tick_chaser_if_due()

            else:
                # Not in chaser mode. If state changed, apply static pattern.
                if self._state != self._last_state:
                    if self._state < 0:
                        # Catch-all: treat other negative states as "all on"
                        self._all_on()
                    else:
                        self._apply_state_static(self._state)
                    self._last_state = self._state

            await asyncio.sleep_ms(poll_ms)
