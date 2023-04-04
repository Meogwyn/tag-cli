import sys
import os
if sys.platform.startswith("linux"):
    import termios
    import tty
import asyncio
import signal
from . import globs
from . import util
from . import uinput # It would be better if this wasn't this way but eh

logsects = {}
cl_tasks = []

def tclog_add_file_sects(file, sects):
    global logsects
    logsects[file] = []
    for sect in sects:
        logsects[file].append(sect)
def filter_depth(depth):
    if globs.Globs["logdepth"] == None:
        return True
    if depth > globs.Globs["logdepth"]:
        return False
    else:
        return True
def filter_sects(sects):
    for sect in sects:
        if globs.Globs["logsects_incl"]:
            if sect not in globs.Globs["logsects_incl"]:
                return False
        if globs.Globs["logsects_excl"]:
            if sect in globs.Globs["logsects_excl"]:
                return False
    return True
"""
Returns True or False depending on whether a logline is respectively fit or 
not for logging
"""
def logfilter(depth, sects):
    if depth:
        if not filter_depth(depth):
            return False
    if sects:
        if not filter_sects(sects):
            return False
    return True
"""
NO LOGGING IN THIS FUNCTION

prints a log entry, optionally prefixed with one or several section 
identifiers, and filtered based on depth
"""
def tclog(rawstr, depth=5000, sects=None):
    if not logfilter(depth, sects):
        return

    logstr = ""

    if sects is not None:
        for sect in sects:
            logstr += f"[{sect}]"
    else:
        logstr += f"[UNDEF]"


    logstr += f" {rawstr}"

    if globs.Globs["logfile"]:
        globs.Globs["logfile"].seek(0, 2)
        globs.Globs["logfile"].write(logstr + "\n")
    if globs.Globs["logstderr"]:
        uinput.prnttext(logstr)

def sigint_hdl(sig = None, frame = None):
    os.write(sys.stdout.fileno(), b'CLI_EXIT\n')
    clean_exit(0)
def panic(err):
    if err:
        print("PANIC: " + err)
        clean_exit(-1)
async def _clean_exit(code):
    try:
        globs.Globs["tag_proc"].send_signal(signal.SIGINT)
    except Exception:
        pass
    for tsk in globs.Globs["tasks"]:
        tsk.cancel()
    if sys.platform.startswith("linux"):
        tty.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, globs.Globs["old_attr"])
def clean_exit(code):
    asyncio.create_task(_clean_exit(code))
