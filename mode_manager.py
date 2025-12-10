# mode_manager.py

import uasyncio as asyncio
import config


class ModeManager:
    def __init__(self, time_provider, schedule_manager, menorah, status_manager=None):
        self._time = time_provider
        self._schedule = schedule_manager
        self._menorah = menorah
        self._status = status_manager

        self._last_state = None

    async def run(self):
        from status_manager import ERR_TIME_INVALID  # late import

        while True:
            # Time validity
            if not self._time.is_valid():
                if self._status:
                    self._status.set_error(ERR_TIME_INVALID)
                effective_state = -1  # act like "outside Hanukkah"
            else:
                if self._status:
                    self._status.clear_error(ERR_TIME_INVALID)
                y, m, d, hh, mm, ss = self._time.get_time()
                effective_state = self._schedule.get_state((y, m, d, hh, mm, ss))

            self._set_state_with_trace(effective_state)
            await asyncio.sleep(config.MODE_POLL_INTERVAL)

    def _set_state_with_trace(self, state: int):
        """
        Apply state to MenorahController and print transitions.

        state:
          -1  outside Hanukkah (default)
           0  Hanukkah daytime (off)
          1-8 Hanukkah nights
        """
        if state == self._last_state:
            return

        # Timestamp for logging
        try:
            y, m, d, hh, mm, ss = self._time.get_time()
        except Exception:
            y, m, d, hh, mm, ss = (0, 0, 0, 0, 0, 0)

        ts = "%04d-%02d-%02d %02d:%02d:%02d" % (y, m, d, hh, mm, ss)

        print("[MODE] %s state=%s" % (ts, str(state)))

        # Candle on/off markers:
        if (self._last_state is None or self._last_state <= 0) and state > 0:
            print("[CANDLES] ON  at %s (night %s)" % (ts, str(state)))
        if self._last_state is not None and self._last_state > 0 and state <= 0:
            print("[CANDLES] OFF at %s (prev night %s)" % (ts, str(self._last_state)))

        self._last_state = state

        # Push to hardware
        self._menorah.set_state(state)
