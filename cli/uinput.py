import sys
import traceback
import select
import asyncio
from . import util
from . import globs
from . import ipccli
from . import cmds
import re
if sys.platform.startswith("linux"):
    import termios
    import tty
elif sys.platform == "win32":
    import msvcrt
"""
A websocat-like client for sending messages to the ipc server
"""

util.tclog_add_file_sects(__file__, ["INP"])

prompt = "tag-cli=>"
inpbuf = "" # raw input buffer
finpbuf = "" # formatted input (with the addition of a prompt, that is)

def clear_fib():
    print("\r" + " " * len(finpbuf) + "\r", end = "")
def prntprmt(): # Print prompt - called after every input and every other print
    global finpbuf
    clear_fib()
    finpbuf = prompt + inpbuf.strip()
    print("\r" + finpbuf, end = "")
def prnttext(text):
    clear_fib()
    print(text)
    prntprmt()





if sys.platform.startswith("linux"):
    def data_rdy():
        res = select.select([sys.stdin], [], [], 0) 
        return res == ([sys.stdin], [], [])


    async def uinp_task():
        global Globs
        global inpbuf
        locsects = util.logsects[__file__]
        try:
            msg = None
            stdin = sys.stdin.fileno()
#            oldattr = termios.tcgetattr(stdin)

            globs.Globs["old_attr"] = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(stdin, termios.TCSANOW)

            i = 0
            while True:
                i += 1
                if data_rdy():
                    msg = sys.stdin.read(1)
                    if ord(msg) == ord("\n"):
                        print("")
                        await parse_cmd(inpbuf)
                        inpbuf = ""
                        prntprmt()
                        continue
                    elif ord(msg) == 127:
                        try:
                            inpbuf = inpbuf.removesuffix(inpbuf[-1])
                        except IndexError:
                            pass
                    elif not msg.isprintable():
                        continue
                    else:
                        inpbuf += msg
                    prntprmt()

                await asyncio.sleep(0.001)
        except asyncio.CancelledError as e:
            util.tclog("user input task exiting", 1000, locsects)
        finally:
            pass
elif sys.platform == "win32":
    locsects = util.logsects[__file__]
    async def uinp_task():
        try:
            global inpbuf
            global lnfull
            msg = None
            skip = False
            while True:
                if msvcrt.kbhit():
                    msg = msvcrt.getch()

                    if skip:
                        skip = False
                        continue

                    """
                    if msg == b'\0':
                        pass
                    """
                    if msg == b'\r':
                        print("")
                        await parse_cmd(inpbuf)
                        inpbuf = ""
                    elif msg == b'\b':
                        try:
                            inpbuf = inpbuf.removesuffix(inpbuf[-1])
                        except IndexError:
                            pass
                    elif not msg.decode().isprintable():
                        pass
                    else:
                        inpbuf += msg.decode()
                    prntprmt()
                    skip = True
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            util.tclog("user input task exiting", 1000, locsects)

else:
    util.panic("unsupported platform")

"""
both funcs return tuple containing string containing argument obtained from 
position cur in cmd_str and the cur of the first non-argument char following 
this arg in cmd_str (which may be 1 over the last char of the string).
"""
def getarg_unquot(cmd_str, cur):
    out_str = ""
    while cur < len(cmd_str):
        if not cmd_str[cur].isspace():
            out_str += cmd_str[cur]
        else:
            break
        cur += 1
    return out_str, cur

def getarg_quot(cmd_str, cur):
    out_str = ""
    spec_chars = "'^"
    term = False
    if not cmd_str[cur] == "'":
        panic("tried to call getarg_quot on non-quoted argument")

    cur += 1
    while True:
        if cur == len(cmd_str):
            raise Exception("unterminated single quote in submitted buffer")

        if cmd_str[cur] == "'":
            cur += 1
            break
        elif cmd_str[cur] == "^":
            if cur + 1 == len(cmd_str):
                raise Exception("unterminated escape char '\\' in submitted buffer")
            if not cmd_str[cur + 1] in spec_chars:
                raise Exception("escape char '\\' used before non-special character in buffer (use '\\\\' if you wish to insert a single '\\' character into the buffer)")
            out_str += cmd_str[cur + 1]
            cur += 1 # cur ends up being bumped two times, which is intended
        else:
            out_str += cmd_str[cur]

        cur += 1

    return out_str, cur

"""
returns a split version of cmd_str
"""
def fmt_cmd(cmd_str):
    out = []
    arg = None
    cur = 0

    while cur < len(cmd_str):
        if cmd_str[cur] == "'":
            arg, cur = getarg_quot(cmd_str, cur)
            out.append(arg)
        elif not cmd_str[cur].isspace():
            arg, cur = getarg_unquot(cmd_str, cur)
            out.append(arg)
        cur += 1
    return out


async def parse_cmd(msg):
    locsects = util.logsects[__file__]
    reg = re.compile("\s+")
    cmd = None

    try: 
        cmd = fmt_cmd(msg)
        util.tclog(f"full command '{cmd}'", 5000, locsects)

        if not len(cmd):
            return
        elif len(cmd) > 1:
            await cmds.run_cmd(cmd[0], cmd[1:])
        else:
            await cmds.run_cmd(cmd[0])
    except Exception as e:
        if cmd:
            util.tclog(f"command {cmd[0]} failed; error: {str(e)}; tb: {traceback.format_exc()}", 5000, locsects)
        else:
            util.tclog(f"input buffer parsing failed: {str(e)}; tb: {traceback.format_exc()}", 5000, locsects)

