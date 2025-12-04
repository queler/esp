# mode_manager.py

import uasyncio as asyncio
import config
from schedule_manager import WINDOW_NONE, WINDOW_LIT, WINDOW_DARK

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
        while True:
            if not self._time.is_valid():
                if self._status:
                    self._status.set_error("time_invalid")
                # Maybe tell menorah to go into an "error idle" mode
                self._menorah.set_mode(MODE_DEFAULT, night=None)
                await asyncio.sleep(config.MODE_POLL_INTERVAL)
                continue
            else:
                if self._status:
                    self._status.clear_error("time_invalid")

            y, m, d, hh, mm, ss = self._time.get_time()
            ymd = (y, m, d)
            ymd_hms = (y, m, d, hh, mm, ss)

            is_h = self._schedule.is_today_hanukkah(ymd)
            if not is_h:
                # Outside Hanukkah: default mode only
                self._menorah.set_mode(MODE_DEFAULT, night=None)
                await asyncio.sleep(config.MODE_POLL_INTERVAL)
                continue

            night = self._schedule.get_night(ymd)
            window = self._schedule.get_window(ymd_hms)

            if window == WINDOW_LIT:
                self._menorah.set_mode(MODE_HANUKKAH_LIT, night=night)
            elif window == WINDOW_DARK:
                self._menorah.set_mode(MODE_HANUKKAH_DARK, night=night)
            else:
                # Should not happen, but treat as dark Hanukkah
                self._menorah.set_mode(MODE_HANUKKAH_DARK, night=night)

            await asyncio.sleep(config.MODE_POLL_INTERVAL)
