import asyncio
import dotenv
import re
import datetime
import signal
import sys
import os
from . import globs
from . import uinput
from . import util

util.tclog_add_file_sects(__file__, ["MAIN"])

def load_envvars():
    global Globs
    if not os.path.exists(".env"):
        open(".env", "w").close() # simple way to create env file
    globs.Globs["env"] = dotenv.dotenv_values(".env")
    globs.Globs["env"].update(os.environ) #cmd-line overwrites vars from 
def set_globs():
    global Globs

    repat = re.compile("\s*")

    if "TC_LOGDEPTH" in globs.Globs["env"]:
        globs.Globs["logdepth"] = int(globs.Globs["env"]["TC_LOGDEPTH"])
    else:
        globs.Globs["logdepth"] = 5000

    #format of TC_LOGSECTS_* is `"<SECT>"[, ...]`
    #if neither is set, all sections are included by default

    #logsects[__file__] to exclude in util.taglog() calls
    if "TC_LOGSECTS_INCL" in globs.Globs["env"]:
        globs.Globs["logsects_incl"] = (re.sub(repat, "", globs.Globs["env"]["TC_LOGSECTS_INCL"])).split(',')
    #logsects[__file__] to exclude in util.taglog() calls
    elif "TC_LOGSECTS_EXCL" in globs.Globs["env"]:
        globs.Globs["logsects_excl"] = (re.sub(repat, "", globs.Globs["env"]["TC_LOGSECTS_EXCL"])).split(',')
    if "TC_LOGSTDERR" in globs.Globs["env"]:
        if globs.Globs["env"]["TC_LOGSTDERR"].lower() == "true":
            re.sub(repat, "", globs.Globs["env"]["TC_LOGSTDERR"])
            globs.Globs["logstderr"] = True
        if globs.Globs["env"]["TC_LOGSTDERR"].lower() == "false":
            globs.Globs["logstderr"] = False
    else:
        globs.Globs["logstderr"] = True

    if "TC_LOGFILE_MODE" in globs.Globs["env"]:
        globs.Globs["logfile_mode"] = globs.Globs["env"]["TC_LOGFILE_MODE"]
    else:
        globs.Globs["logfile_mode"] = "r+"


    if "TC_LOGFILE" in globs.Globs["env"]:
        globs.Globs["logfile"] = open(globs.Globs["env"]["TC_LOGFILE"], globs.Globs["logfile_mode"])

async def pootask():
    locsects = util.logsects[__file__]
    while True:
        util.tclog('poo', 0, locsects)
        await asyncio.sleep(1)

async def main():
    #no logging before these two
    load_envvars()
    set_globs()

    util.tclog(f"[START {datetime.datetime.now()}]", depth = 1)

    signal.signal(signal.SIGINT, util.sigint_hdl)

    util.tclog(f"env vars:{globs.Globs['env']}", sects = util.logsects[__file__], depth = 5000)
#    asyncio.gather(uinput.uinp_task(), pootask())
    await asyncio.gather(uinput.uinp_task())
    


if __name__ == "__main__":
    asyncio.run(main())
