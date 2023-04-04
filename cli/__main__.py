import asyncio
import traceback
import dotenv
import re
import datetime
import signal
import sys
import os
from . import globs
from . import uinput
from . import util
from . import ipccli
from . import ipcparser

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

    if "TAG_TCP_HOST" in globs.Globs["env"]:
        globs.Globs["tcp_host"] = globs.Globs["env"]["TAG_TCP_HOST"]
    else:
        globs.Globs["tcp_host"] = "localhost" 

    if "TAG_TCP_PORT" in globs.Globs["env"]:
        globs.Globs["tcp_port"] = int(globs.Globs["env"]["TAG_TCP_PORT"])
    else:
        globs.Globs["tcp_port"] = 15324

async def pootask():
    locsects = util.logsects[__file__]
    while True:
        util.tclog('poo', 0, locsects)
        await asyncio.sleep(1)

async def tag_task():
    #globs.Globs["tag_proc"] = 
    locsects = ["TTASK"]
    try:
        util.tclog("tag task starting", 1000, locsects)
        proc = await asyncio.create_subprocess_shell("python -m tag.tag", stdout = None)
        await proc.wait()
    except asyncio.CancelledError as e:
        proc.send_signal(signal.SIGINT)
        util.tclog("tag task exiting", 1000, locsects)
        raise



async def main():
    global Globs
    #no logging before these two
    load_envvars()
    set_globs()

    util.tclog(f"[START {datetime.datetime.now()}]", depth = 1)


    util.tclog(f"env vars:{globs.Globs['env']}", sects = util.logsects[__file__], depth = 5000)

    sys.path.append("tag/")
    uinp_tsk = asyncio.create_task(uinput.uinp_task())
    parse_tsk = asyncio.create_task(ipcparser.parse_task())
    ipc_tsk = asyncio.create_task(ipccli.ipc_task())
    tag_tsk = asyncio.create_task(tag_task())

    globs.Globs["tasks"] += [uinp_tsk, parse_tsk, ipc_tsk, tag_tsk]
    if sys.platform.startswith("linux"):
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, util.sigint_hdl)
    for i in globs.Globs["tasks"]:
        print(f'CREATED TASK {i}')
    try:
        await asyncio.gather(uinp_tsk, 
                             parse_tsk, 
                             ipc_tsk,
                             tag_tsk)
    except asyncio.CancelledError as e:
        print(f"weird CancelledError: {repr(e)}, tb: {traceback.format_exc()}")
    except SystemExit as e:
        print(f"sysexit: {repr(e)}")
    


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit as e:
        pass
