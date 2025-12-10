# mode_manager.py

import uasyncio as asyncio
import config
from schedule_manager import WINDOW_NONE, WINDOW_LIT, WINDOW_DARK
from time_provider import DebugTimeProvider
MODE_HANUKKAH_LIT = 1
MODE_HANUKKAH_DARK = 2
MODE_DEFAULT = 3


class ModeManager:
    def __init__(self, time_provider, schedule_manager, menorah, status_manager=None):
        self._time = time_provider
        self._schedule = schedule_manager
        self._menorah = menorah
        self._status = status_manager

    async def run(self):
        from status_manager import ERR_TIME_INVALID  # late import

        while True:
            if not self._time.is_valid():
                if self._status:
                    self._status.set_error(ERR_TIME_INVALID)
                # Without valid time, safest is a neutral/default mode
                self._menorah.set_mode(MODE_DEFAULT, night=None)
                await asyncio.sleep(config.MODE_POLL_INTERVAL)
                continue
            else:
                if self._status:
                    self._status.clear_error(ERR_TIME_INVALID)

            y, m, d, hh, mm, ss = self._time.get_time()
            ymd = (y, m, d)
            ymd_hms = (y, m, d, hh, mm, ss)

            window = self._schedule.get_window(ymd_hms)

            if window == WINDOW_NONE:
                # Not a Hanukkah date at all
                self._menorah.set_mode(MODE_DEFAULT, night=None)
            else:
                night = self._schedule.get_night(ymd)
                if window == WINDOW_LIT:
                    self._menorah.set_mode(MODE_HANUKKAH_LIT, night=night)
                elif window == WINDOW_DARK:
                    self._menorah.set_mode(MODE_HANUKKAH_DARK, night=night)
                else:
                    # belt-and-suspenders
                    self._menorah.set_mode(MODE_HANUKKAH_DARK, night=night)
            if isinstance(self._time,DebugTimeProvider):
                await asyncio.sleep(
                    config.MODE_POLL_INTERVAL / self._time._speed   # in simulated seconds
                                    )
            else:
                await asyncio.sleep(config.MODE_POLL_INTERVAL)
