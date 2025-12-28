import config
from schedule_events import EVENTS
from solar import SolarCache
s=SolarCache(config.LATITUDE,
             config.LONGITUDE,
             config.TIMEZONE_OFFSET_MINUTES
             ,60, -60)
for Y,M,D,h,m,status in EVENTS:
    obsr,obss=s.sunrise_sunset(Y,M,D)
    if status==0:
        #sunrises
        hm=obsr
    else:
        hm=obss
    obh=int(hm/60) # pyright: ignore[reportOptionalOperand]
    obm=int(hm%60)         # pyright: ignore[reportOptionalOperand]
    if (h,m)!=(obh,m):
        print(Y,M,D,f"{h}:{m:0>2} new: {obh}:{obm:0>2} -- {(h,m)==(obh,m)}")
