# schedule_manager.py

from schedule_data import SCHEDULE

WINDOW_NONE = "none"
WINDOW_LIT = "lit"
WINDOW_DARK = "dark"


class ScheduleManager:
    def __init__(self, entries):
        # Map (Y, M, D) -> (night, start_min, end_min)
        self._by_date = {}
        for (y, m, d, night, start_min, end_min) in entries:
            self._by_date[(y, m, d)] = (night, start_min, end_min)

    def get_entry(self, ymd):
        """Return (night, start_min, end_min) or None."""
        return self._by_date.get(ymd, None)

    def is_today_hanukkah(self, ymd):
        """True if this civil date has a Hanukkah entry."""
        return ymd in self._by_date

    def get_night(self, ymd):
        entry = self._by_date.get(ymd)
        if entry is None:
            return None
        return entry[0]

    def get_window(self, ymd_hms):
        """
        ymd_hms: (Y, M, D, h, m, s)
        Returns:
            WINDOW_NONE  -> not a Hanukkah date
            WINDOW_LIT   -> within lighting window
            WINDOW_DARK  -> Hanukkah date, but outside window
        """
        y, m, d, hh, mm, ss = ymd_hms
        entry = self._by_date.get((y, m, d))
        if entry is None:
            return WINDOW_NONE

        night, start_min, end_min = entry
        minutes = hh * 60 + mm

        # TWO CASES:
        # 1) Non-wrap window: start <= end (all on same civil day)
        #    Lit if start <= minutes < end.
        # 2) Wrap-around window: start > end (evening -> next morning)
        #    Lit if minutes >= start OR minutes < end.
        if start_min <= end_min:
            if start_min <= minutes < end_min:
                return WINDOW_LIT
            else:
                return WINDOW_DARK
        else:
            # Wrap-around: like [start..24:00) U [0..end)
            if minutes >= start_min or minutes < end_min:
                return WINDOW_LIT
            else:
                return WINDOW_DARK
