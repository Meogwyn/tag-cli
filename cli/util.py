import sys
import asyncio
from . import globs
from . import uinput # It would be better if this wasn't this way but eh

logsects = {}

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
#        asyncio.create_task(aioconsole.aprint(logstr, use_stderr = True))

def sigint_hdl(sig, frame):
    print('EXIT')
    clean_exit(0)
def panic(err):
    if err:
        print("PANIC: " + err)
        clean_exit(-1)
def clean_exit(code):
    exit(code)
