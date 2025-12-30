import config
import dttuple
import heb
from schmaninterface import SchManInterface
from solar import SolarCache


class Han(SchManInterface):

    hd : int
    hy:int
    hmo :int
    valid_until: tuple[int,... ]
    _start:list[tuple[int,...] ]
    _end:list[tuple[int,...]]
    _holiday_end:"tuple[int,int,int,int,int]"
    ymd: tuple[int,int,int]
    sch_hy:int
    events:list[tuple[int,...]]
    def __init__(self, dt:tuple[int,...]):

        # if ymd is None:
        #     ymd = time.localtime()
        self.reinit(dt)

    def reinit(self, dt:tuple[int,...]):
        # noinspection PyTypeChecker
        self._start = [None] * 8
        # noinspection PyTypeChecker
        self._end = [None] * 8
        # noinspection PyTypeChecker
        self.ymd = dt[:3]
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
            # night ends at sunrise of next day
            self._start[i] = nth_ymd + (sunset_today // 60, sunset_today % 60)
            self._end[i] = np1_ymd + (sunrise_next // 60, sunrise_next % 60)
        #TODO: do I want wait untill sundown *9* to start -1 mode
        i=9
        nth_ymd = dttuple.add_days(*first_ymd, i)
        sunrise_today, sunset_today = solar.sunrise_sunset(*nth_ymd)
        self._holiday_end = nth_ymd + (int(sunset_today // 60), int(sunset_today % 60))


        self.events = self.gen_events()
        self.valid_until:"tuple[int,int,int]" = heb.to_gregorian(self.sch_hy, heb.TEVETH, 4)

    def is_expired(self, dt:tuple[int,...]) -> bool:
        #if tp is None:
        #    raise ValueError('i don\'t want to implement yet')
        #    #tp = time.localtime()
        return dt[:3] >= self.valid_until

    def first_ymd_h_night(self):
        self.hy, self.hmo, self.hd = heb.from_gregorian(*self.ymd)

        # If we're already safely past early Tevet, schedule next year's Hanukkah
        if (self.hmo > heb.TEVETH) or (self.hmo == heb.TEVETH and self.hd >= 4):
            self.sch_hy = self.hy + 1
        else:
            self.sch_hy = self.hy

        # Return the civil date whose sunset begins 25 Kislev (i.e., civil day before 25 Kislev)
        return heb.to_gregorian(self.sch_hy, heb.KISLEV, 24)

    def gen_events(self) -> list[tuple[int,...]]:
        assert len(self._start) == 8 and len(self._end) == 8
        es = []
        for i in range(8):
            night = i + 1
            es.append(self._start[i] + (night,))
            es.append(self._end[i] + (0,))
        es.append(self._holiday_end)
        return es

    def get_state(self, ymd_hms: tuple[int, ...]) -> int:
        if self.is_expired(ymd_hms):
            self.reinit(ymd_hms)
        state = -1
        for event in self.events:
            if ymd_hms[:5] < event[:5]:
                return state
            else:
                state = event[-1]
        return -1

    def test(self):
        import time
        for i in range(time.mktime((2025, 12, 10, 10, 0, 0,0,0)), time.mktime((2026,1,1,0,0,0,0,0)), 12 * 60 * 61):
            print(time.localtime(i),self.get_state(time.localtime(i)))

