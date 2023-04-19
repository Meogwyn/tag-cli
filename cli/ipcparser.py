import asyncio
import traceback
import re
import json
from . import util
from . import ipccli
from . import globs
from . import cmds

util.tclog_add_file_sects(__file__, ["TC_IPC_PARSER"])
parseq = asyncio.Queue()

def parseq_push_msg(msg):
    global parseq
    locsects = util.logsects[__file__]

    try:
        locsects = util.logsects[__file__]
        util.tclog(f"trying to push message {msg} to parseq", 5000, locsects)
        parseq.put_nowait(json.loads(msg))
    except Exception as e:
        util.tclog(f"failed to push message {msg} to parseq; error: {repr(e)}", 5000, locsects)
async def parse_task():
    locsects = util.logsects[__file__]
    msg = None

    util.tclog("starting ipc parser", 1000, locsects)
    while True:
        try:
            msg = await parseq.get()
            parse_ipc_msg(msg)
        except asyncio.CancelledError:
            util.tclog("ipc parser task exiting", 1000, locsects)
            raise
        except Exception as e:
            util.tclog(f"failed to parse server message {msg}; error: {repr(e)}", 5000, locsects)

def parse_ipc_msg(msg):
    locsects = ["SERV_MSG"]

    if not "type" in msg:
        raise Exception("ipc message missing 'type'")
    if "err" in msg:
        util.tclog(f"TAG call '{msg['type']}' failed; error: {msg['err']}", 0, locsects)
    else:
        util.tclog(f"TAG call '{msg['type']}' succeeded", 0, locsects)

    try:
        match (msg["type"]): # server message hooks
            case "ping":
                util.tclog(f"tag server ping; tag_prot version: {msg['data']['tag_prot_vers']} TAG version: {msg['data']['tag_prot_vers']}", 0, locsects)
            case "get_pkg_config":
                util.tclog(f"loaded pc: {json.dumps(msg['data'], indent = 4)}", 0, locsects)
                cmds.setpc(msg["data"])
            case "all_pkg_configs":
                # printed data includes only name, id
                outstr = "saved pcs: \n"
                for i in msg['data']:
                    outstr += "----------------\n"
                    outstr += f"name: '{i['name']}' id: '{i['id']}'\n"
                outstr += "----------------\n"
                util.tclog(outstr, 0, locsects)
            case "all_runs":
                outstr = "saved runs: \n"
                for i in msg['data']:
                    outstr += "----------------\n"
                    outstr += f"pc name: '{i['pkg']['name']}' pc id: '{i['pkg']['id']}' run id: '{i['run_id']}'\n"
                outstr += "----------------\n"
                util.tclog(outstr, 0, locsects)
            case "status":
                util.tclog(f"TAG status dump: {json.dumps(msg['data'], indent = 4)}", 0, locsects)
            case "start":
                util.tclog(f"started on pc (id: '{msg['data']['id']}', run_id: '{msg['data']['run_id']}')", 0, locsects)
            case "pkg_success":
                util.tclog(f"pc '{msg['data']['name']}' (id: '{msg['data']['id']}', run_id '{msg['data']['run_id']}') SUCCESSFUL", 0, locsects)
            case "pkg_failure":
                util.tclog(f"pc '{msg['err']['name']}' (id: '{msg['err']['id']}', run_id '{msg['err']['run_id']}') FAILED (ERROR: {msg['err']['desc']})", 0, locsects)
            case _:
                if "err" in msg:
                    pass
                elif "data" in msg:
                    util.tclog(f"hookless server message: {json.dumps(msg['data'], indent = 4)}", 0, locsects)
                else:
                    util.tclog(f"hookless server message of type {msg['type']} without data!", 0, locsects)

    except Exception as e:
        util.tclog(f"response to server message {msg['type']} failed; error: {repr(e)} \ntraceback: {traceback.format_exc()}", 0, locsects)
