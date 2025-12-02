# main.py
import os

AUTO = "autorun.flag"

if AUTO in os.listdir():
    print("AUTO MODE ENABLED — running realmain.")
    import realmain
    import uasyncio
    uasyncio.run(realmain.run())
else:
    print("SAFE MODE — nothing auto-run.")
    print("You can now: mpremote soft-reset; mpremote mount . ; exec realmain")
