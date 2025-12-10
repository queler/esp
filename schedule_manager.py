# schedule_manager.py

from schedule_events import EVENTS


class ScheduleManager:
    """
    Event-based schedule with a cursor.

    EVENTS entries are:
        (year, month, day, hour, minute, state)

    state:
        1..8  = Hanukkah night N (candles ON)
        0     = Hanukkah daytime (candles OFF)
       -1     = explicit "outside Hanukkah" marker

    If there is no event at or before 'now', we return -1.
    """

    def __init__(self, events=None):
        if events is None:
            events = EVENTS

        # Ensure sorted by absolute time
        self._events = sorted(events, key=self._key)
        self._index = -1
        self._last_key = None  # last (Y, M, D, hh, mm) we saw

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _key(e):
        y, m, d, hh, mm, state = e
        return (y, m, d, hh, mm)

    @staticmethod
    def _now_key(ymd_hms):
        y, m, d, hh, mm, ss = ymd_hms
        return (y, m, d, hh, mm)

    def _find_index(self, now_key):
        """
        Binary search for the last event with time <= now_key.
        Returns -1 if all events are in the future.
        """
        events = self._events
        lo = 0
        hi = len(events) - 1
        best = -1

        while lo <= hi:
            mid = (lo + hi) // 2
            if self._key(events[mid]) <= now_key:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    def _state_from_index(self):
        """
        Convert current index into a state integer.
        """
        if self._index < 0:
            return -1  # before first event: "outside Hanukkah"
        _, _, _, _, _, state = self._events[self._index]
        return state

    # ---- public API -----------------------------------------------------

    def get_state(self, ymd_hms):
        """
        Return integer state for the given time:

            1..8  = Hanukkah night N (candles ON)
            0     = Hanukkah daytime (candles OFF)
           -1     = outside Hanukkah entirely

        Maintains a cursor so we only do a full search when time moves
        backwards or on the first call.
        """
        now_key = self._now_key(ymd_hms)

        # First call: full search
        if self._last_key is None:
            self._index = self._find_index(now_key)
            self._last_key = now_key
            return self._state_from_index()

        # Time moved backwards (e.g. DebugTimeProvider.set_time, NTP jump)
        if now_key < self._last_key:
            self._index = self._find_index(now_key)
            self._last_key = now_key
            return self._state_from_index()

        # Normal forward progression: walk forward while future events
        # are still <= now
        events = self._events
        i = self._index
        n = len(events)

        while i + 1 < n and self._key(events[i + 1]) <= now_key:
            i += 1

        self._index = i
        self._last_key = now_key
        return self._state_from_index()
