# menorah.py

import uasyncio as asyncio
import time
import config

# Bit mappings (MSB -> LSB)
MONTH_BITS = (8, 7, 6, 5)
DAY_BITS   = (0, 4, 3, 2, 1)

HOUR_BITS  = (8, 7, 6, 5)
FACE_BITS  = (4, 3, 2, 1)
PM_BIT     = 0


def _bits_to_indices(value: int, idxs_msb_to_lsb):
    width = len(idxs_msb_to_lsb)
    on = []
    for i, idx in enumerate(idxs_msb_to_lsb):
        bitpos = width - 1 - i
        if (value >> bitpos) & 1:
            on.append(idx)
    return on


def _render_date(dt6):
    # dt6: (Y, M, D, h, m, s)
    month = dt6[1]
    day = dt6[2]
    on = []
    on += _bits_to_indices(month, MONTH_BITS)
    on += _bits_to_indices(day, DAY_BITS)
    return on


def _render_time(dt6):
    hh = dt6[3]
    mm = dt6[4]

    pm = 1 if hh >= 12 else 0

    hour12 = hh % 12
    if hour12 == 0:
        hour12 = 12

    face = mm // 5  # 0..4

    on = []
    on += _bits_to_indices(hour12, HOUR_BITS)
    on += _bits_to_indices(face, FACE_BITS)
    if pm:
        on.append(PM_BIT)
    return on

class MenorahController:
    """
    -1  = outside Hanukkah (digital clock/calendar)
     0  = Hanukkah daytime, candles OFF
    1-8 = Hanukkah night N, candles ON
    """

    def __init__(self, candles, shamash_index=0):
        self._candles = list(candles)
        if not self._candles:
            raise ValueError("MenorahController requires at least one candle")

        self._shamash_index = shamash_index

        self._state: int = -1
        self._last_state: int = -2

        # Clock/calendar idle mode
        self._time_fn = None  # set via set_time_fn()
        self._idle_view = 0  # 0=date, 1=time
        self._idle_last_ms = time.ticks_ms()
        self._idle_date_ms = int(getattr(config, "IDLE_DATE_SECONDS", 2) * 1000)
        self._idle_time_ms = int(getattr(config, "IDLE_TIME_SECONDS", 5) * 1000)
        self._idle_last_on = None  # last "on set" to avoid churn

    def set_time_fn(self, fn):
        # fn should return (Y,M,D,h,m,s)
        self._time_fn = fn

    # ... keep your existing _all_off/_all_on/_apply_state_static/_apply_hanukkah_lit etc ...

    def _apply_bits(self, on_indices):
        # Convert to a set, ignore out-of-range indices
        desired = set(i for i in on_indices if 0 <= i < len(self._candles))
        if self._idle_last_on == desired:
            return

        for i, c in enumerate(self._candles):
            if i in desired:
                c.on()
            else:
                c.off()

        self._idle_last_on = desired

    def _tick_idle_clock(self):
        # If we don't have time yet, just go dark.
        if self._time_fn is None:
            self._all_off()
            return

        now = time.ticks_ms()
        dur = self._idle_date_ms if self._idle_view == 0 else self._idle_time_ms
        if time.ticks_diff(now, self._idle_last_ms) >= dur:
            self._idle_view ^= 1
            self._idle_last_ms = now
            self._idle_last_on = None  # force refresh on view switch

        dt6 = self._time_fn()
        on = _render_date(dt6) if self._idle_view == 0 else _render_time(dt6)
        self._apply_bits(on)

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


    # ------------------------------------------------------------------
    # Task
    # ------------------------------------------------------------------


    async def run(self, poll_ms: int = 100) -> None:
        while True:
            if self._state == -1:
                # Outside Hanukkah: show clock/calendar
                self._tick_idle_clock()
            else:
                # Apply static Hanukkah patterns on state changes
                if self._state != self._last_state:
                    if self._state < 0:
                        self._all_on()
                    else:
                        self._apply_state_static(self._state)
                    self._last_state = self._state

            await asyncio.sleep_ms(poll_ms)