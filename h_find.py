import heb
import time
#from time_provider import BaseTimeProvider
def first_ymd_h_night(ymd):
    Y, M, D=ymd
    hy,hm,hd=heb.from_gregorian(Y,M,D)
    if      ((hm>heb.TEVETH) or \
            (hm==heb.TEVETH and hd>4)):
        sch_year=hy+1
    else:
        sch_year=hy+int(hm>(heb.KISLEV+1))
    return heb.to_gregorian(sch_year,heb.KISLEV,25-1) #to get the night
def test()
    for d in range(21,32,1):
        ymd=(2025,12,d)
        print(f"{ymd}:{first_ymd_h_night(ymd)}")
