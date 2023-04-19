import asyncio
import json
from . import util
from . import ipcparser
from . import globs

util.tclog_add_file_sects(__file__, ["TC_IPC_CLI"])

sendq = asyncio.Queue()

rdr_tsk = None 
wtr_tsk = None 

"""
Sends a string over the TCP connection
"""
def send(msg):
    sendq.put_nowait(msg)
"""
Sends a dict over the TCP connection
"""
def send_dict(msg):
    send(json.dumps(msg))
async def ipc_task():
    global rdr_tsk, wtr_tsk
    locsects = list(util.logsects[__file__])
    rdr = None
    wtr = None
    util.tclog(f"establishing TCP connection to TAG...", 1000, locsects)

    tries = 0
    try:
        while tries < 50:
            try:
                rdr, wtr = await asyncio.open_connection(globs.Globs["tcp_host"], globs.Globs["tcp_port"])
                break
            except OSError:
                tries += 1
                util.tclog(f"failed to connect; this is normal for the first few times", 1000, locsects)
                await asyncio.sleep(0.1)
        util.tclog(f"connected to TAG with tag_prot version 1.0", 1000, locsects)
        rdr_tsk = asyncio.create_task(rdr_task(rdr))
        wtr_tsk = asyncio.create_task(wtr_task(wtr))
    except Exception as e:
        util.tclog(f"couldn't establish connection to subprocess; error: {repr(e)}")
        util.panic(f"couldn't establish connection to subprocess; error: {repr(e)}")
    while True:
        await asyncio.sleep(10)
async def wtr_task(wtr):
    locsects = list(util.logsects[__file__])
    locsects += ["WTR"]
    while True:
        try:
            msg = await sendq.get()
            fmsg = int.to_bytes(len(msg.encode()), 4, "big") + msg.encode()
            util.tclog(f"sending msg '{fmsg}'", 5000, locsects)
            wtr.write(fmsg)
            await wtr.drain()
        except asyncio.CancelledError:
            util.tclog("ipc writer task exiting", 1000, locsects)
            raise
async def rdr_task(rdr):
    locsects = list(util.logsects[__file__])
    bytes_read = 0
    locsects += ["RDR"]
    while True:
        try:
            msglen = await rdr.readexactly(4)
            msg = await rdr.readexactly(int.from_bytes(msglen, 'big'))
            if not len(msg):
                raise asyncio.CancelledError()
            util.tclog(f"received msg: '{msg}'", 5000, locsects)
            ipcparser.parseq_push_msg(msg.decode())
        except asyncio.CancelledError:
            util.tclog("ipc reader task exiting", 1000, locsects)
            wtr_tsk.cancel()
            raise
        except asyncio.IncompleteReadError:
            util.panic("unexpected EOF from TAG; possibly, the client should be restarted")
#            util.clean_exit(-1)
