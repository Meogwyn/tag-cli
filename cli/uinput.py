import sys
import traceback
import select
import asyncio
from . import util
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
    finpbuf = prompt + inpbuf
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
        try:
            global inpbuf
            global lnful
            msg = None
            stdin = sys.stdin.fileno()
#            oldattr = termios.tcgetattr(stdin)

            tty.setcbreak(stdin, termios.TCSANOW)

            i = 0
            while True:
                i += 1
                if data_rdy():
                    msg = sys.stdin.read(1)
                    if msg == "\n":
                        parse_cmd(inpbuf)
                        inpbuf = ""
                        prntprmt()
                        continue
                    inpbuf += msg
                    prntprmt()

                await asyncio.sleep(0.001)
        except asyncio.CancelledError as e:
            print(f'error: {repr(e)}\n tb: {traceback.format_exc()}')
        finally:
            pass
#            termios.tcsetattr(stdin, termios.TCSANOW, oldattr)
elif sys.platform == "win32":
    async def uinp_task():
        global inbuf
        global lnfull
        msg = None
        skip = False
        while True:
            if msvcrt.kbhit():
                msg = msvcrt.getch()

                if skip:
                    skip = False
                    continue

                if msg == b'\0':
                    if not skip:
                        skip = True
                    continue
                elif msg == b'\r':
                    parse_cmd(inpbuf)
                    inpbuf = ""
                    prntprmt()
                    skip = True
                    continue
                else:
                    inpbuf += msg
                    prntprmt()
                    skip = True
            await asyncio.sleep(0.02)

else:
    util.panic("unsupported platform")

def parse_cmd(msg):
    locsects = util.logsects[__file__]
    reg = re.compile("\s+")
    cmd = re.sub(reg, " ", msg.strip()).split()


    util.tclog(f"full command '{cmd}'", 5000, locsects)

    if not len(cmd):
        return

    match cmd[0]:
        case "":
            print('boo!')
            return
        case _:
            util.tclog(f"command '{cmd[0]}' not found", 0, locsects)
            return 

