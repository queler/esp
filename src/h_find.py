from typing import Any

import config
import dttuple
import heb
from solar import SolarCache
from time_provider import BaseTimeProvider


class Han(i_man):
    hd: int
    hd : int
    hy:int
    hmo :int
    valid_until: tuple[int,... ]
    _start:list[tuple[int,...] ]
    _end:list[tuple[int,...]]
    ymd: tuple[int,int,int]
    sch_hy:int
    events:list[tuple[int,...]]
    def __init__(self, tp: BaseTimeProvider):

        # if ymd is None:
        #     ymd = time.localtime()
        self.reinit(tp)

    def reinit(self, tp:BaseTimeProvider):
        # noinspection PyTypeChecker
        self._start = [None] * 8
        # noinspection PyTypeChecker
        self._end = [None] * 8
        # noinspection PyTypeChecker
        self.ymd = tp.get_time()[:3]
        solar = SolarCache(
            config.LATITUDE,
            config.LONGITUDE,
            config.TIMEZONE_OFFSET_MINUTES,
            config.SUNRISE_FUDGE_MINUTES,  # sunrise fudge first
            config.SUNSET_FUDGE_MINUTES,  # sunset fudge second
        )

        first_ymd = self.first_ymd_h_night()

        for i in range(8):
            nth_ymd = dttuple.add_days(*first_ymd, i)
            np1_ymd = dttuple.add_days(*nth_ymd, 1)

            sunrise_today, sunset_today = solar.sunrise_sunset(*nth_ymd)
            sunrise_next, sunset_next = solar.sunrise_sunset(*np1_ymd)

            # night starts at sunset of nth_ymd
            night_start_mins = sunset_today
            # night ends at sunrise of next day
            night_end_mins = sunrise_next

            self._start[i] = nth_ymd + (night_start_mins // 60, night_start_mins % 60)
            self._end[i] = np1_ymd + (night_end_mins // 60, night_end_mins % 60)
        self.events = self.gen_events()
        self.valid_until = heb.to_gregorian(self.sch_hy, heb.TEVETH, 4)

    def is_expired(self, tp:BaseTimeProvider):
        if tp is None:
            raise ValueError('i don\'t want to implement yet')
            #tp = time.localtime()
        return dttuple.mktimex(*tp.get_time()) >= dttuple.mktimex(*self.valid_until)

    def first_ymd_h_night(self):
        self.hy, self.hmo, self.hd = heb.from_gregorian(*self.ymd)

        # If we're already safely past early Tevet, schedule next year's Hanukkah
        if (self.hmo > heb.TEVETH) or (self.hmo == heb.TEVETH and self.hd >= 4):
            self.sch_hy = self.hy + 1
        else:
            self.sch_hy = self.hy

        # Return the civil date whose sunset begins 25 Kislev (i.e., civil day before 25 Kislev)
        return heb.to_gregorian(self.sch_hy, heb.KISLEV, 24)

    def gen_events(self) -> list[Any]:
        assert len(self._start) == 8 and len(self._end) == 8
        es = []
        for i in range(8):
            night = i + 1
            es.append(self._start[i] + (night,))
            es.append(self._end[i] + (0,))
        return es
