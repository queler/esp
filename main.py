# main.pycomp
import os

AUTO = "autorun.flag"
def _run():
    """Start the main application in auto mode."""
    import realmain
    import uasyncio
    uasyncio.run(realmain.run())
if AUTO in os.listdir():
    print("AUTO MODE ENABLED — running realmain.")
    _run()
else:
    print("SAFE MODE — nothing auto-run.")
    print("You can now: mpremote soft-reset; mpremote mount . ; exec realmain")
