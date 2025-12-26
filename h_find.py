import config
import dttuple
import heb
from solar import SolarCache


class Han:
    def __init__(self, ymd):
        self._y, self._m, self._d = ymd
        self._start = [None] * 8
        self._end   = [None] * 8

        solar = SolarCache(
            config.LATITUDE,
            config.LONGITUDE,
            config.TIMEZONE_OFFSET_MINUTES,
            config.SUNRISE_FUDGE_MINUTES,  # sunrise fudge first
            config.SUNSET_FUDGE_MINUTES,   # sunset fudge second
        )

        first_ymd = self.first_ymd_h_night()

        for i in range(8):
            nth_ymd = dttuple.add_days(*first_ymd, i)
            np1_ymd = dttuple.add_days(*nth_ymd, 1)

            sunrise_today, sunset_today = solar.sunrise_sunset(*nth_ymd)
            sunrise_next,  sunset_next  = solar.sunrise_sunset(*np1_ymd)

            # night starts at sunset of nth_ymd
            night_start_mins = sunset_today
            # night ends at sunrise of next day
            night_end_mins   = sunrise_next

            self._start[i] = nth_ymd + (night_start_mins // 60, night_start_mins % 60)
            self._end[i]   = np1_ymd + (night_end_mins   // 60, night_end_mins   % 60)

    def first_ymd_h_night(self):
        Y, M, D = self._y, self._m, self._d
        hy, hm, hd = heb.from_gregorian(Y, M, D)

        # If we're already safely past early Tevet, schedule next year's Hanukkah
        if (hm > heb.TEVETH) or (hm == heb.TEVETH and hd > 4):
            sch_year = hy + 1
        else:
            sch_year = hy

        # Return the civil date whose sunset begins 25 Kislev (i.e., civil day before 25 Kislev)
        return heb.to_gregorian(sch_year, heb.KISLEV, 24)
