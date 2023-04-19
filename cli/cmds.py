import asyncio
import os
import json
from . import util
from . import globs
from . import ipccli
from tag.tag import schemas


cmds = [] # list of command bindings {<cmdname>, <func>, <usage>, <desc>}

util.tclog_add_file_sects(__file__, ["CMDS"])

# arg checking is to be done inside of the relevant funcs
# if a command fails, an exception is raised

glob_pc = None #package config temp

def setpc(pc):
    global glob_pc
    glob_pc = dict(pc)

async def run_cmd(cmdname, *args):
    global cmds
    cmd = None
    locsects = list(util.logsects[__file__])

    util.tclog(f"attempting to run command {cmdname}", 3000, locsects)

    for i in cmds:
        if i["name"] == cmdname:
            cmd = i

    if not cmd:
        raise Exception(f"command {cmdname} not found")

    util.tclog(f"args: {args}", depth = 3000, sects = locsects)
    cmd["func"](*args)


def prntcmd(cmd):
    locsects = list(util.logsects[__file__])
    util.tclog(f"\nUSAGE: {cmd['name']} {cmd['usage']} \nDESC:'{cmd['desc']}'\n", 0, [f"{cmd['name']}"])

def cmd_help_fnc(*args):
    locsects = list(util.logsects[__file__])
    if not len(args):
        for i in cmds:
            prntcmd(i)
        util.tclog("\n\nGeneral help on inputting commands: commands and the corresponding arguments are generally separated by spaces, but if you wish to submit multiple words as a single argument (say, when specifying a prompt), enclose them in single quotes in the appropriate argument position\n\nEXAMPLE: \nqparam prompt 'Recommend me five kinds of apples'\n\nIf a single quote has to be part of a word in an argument that is enclosed in single quotes, it must be escaped using '^'\n\nEXAMPLE:\nqparam prompt 'what does the word ^'apple^' mean'.\n\nAn 'Enter' key submits the current input buffer.\n\nnote that consecutive whitespace characters get ignored, even in quoted sequences", 0, ["GENHELP"])
        return

    if not len(args[0]) == 1:
        raise Exception("invalid number of args")
    cmdname = args[0][0]
    for i in cmds:
        if cmdname == i["name"]:
            prntcmd(i)
            return
    raise Exception(f"command '{cmdname}' not found")

cmd_help_usage = "[<cmd>]"
cmd_help_desc = "prints this help, or help about <cmd> if specified"

def empty_pc():
    return {
        "max_failures": 10,
        "overwrite": False,
        "oai_config_gen": {},
        "ideas": [],
        "queries": []
    }

def cmd_initpc_fnc(*args):
    global glob_pc 
    locsects = list(util.logsects[__file__])

    if glob_pc:
        raise Exception("another pc is already loaded\nTIP: use clearpc to clear the worked-on pc (this may discard progress)")

    glob_pc = empty_pc()
    showpc(glob_pc)
    util.tclog(f"pc initialized", 0, locsects)


cmd_initpc_usage = ""
cmd_initpc_desc = "initialize package config for configuration"

"""
list for small-brain me:
    1. finish general coerce_val func
    2. code into *param_fnc's 
    3. implement magic exception

sch_list is the object used in the 'properties' section of the schema sub-object
corresponding to the section one needs
"""

def coerce_val(param, val, sch_list):
    locsects = list(util.logsects[__file__])
    shobj = None # schema object

    util.tclog(f"attempting to coerce val '{val}' of param '{param}' from type '{type(val)}'")

    for temp in sch_list:
        if param == temp:
            shobj = sch_list[temp]
            break

    if not shobj:
        raise KeyError('bc82cb068ef102a1f4e296992e5979ef') # magic!
    else:
        util.tclog(f"target type: {shobj['type']}", 5000, locsects)

    match shobj["type"]:
        case "integer":
            val = int(val)
        case "boolean":
            match val.lower():
                case "true":
                    val = True
                case "false":
                    val = False
                case _:
                    raise Exception(f"expected bool ('true' | 'false') for param {param}")
        case "object":
            raise Exception(f"attempted to set protected parameter...")
        case "array":
            raise Exception(f"attempted to set protected parameter...")
        case _:
            pass
    util.tclog(f"coerce_val output for param '{param}': '{val}', type: '{type(val)}'", 5000, locsects)
    return val


def cmd_submit_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    util.tclog(f"submitting pc: {json.dumps(glob_pc, indent = 4)}", 0, locsects)

    ipccli.send_dict({
        "type":"create_pkg_config", 
        "data": {"pkgc": glob_pc}
    })

cmd_submit_usage = ""
cmd_submit_desc = "submit pkg config to TAG"

def empty_query():
    return {
        "oai_config": {},
        "inp_cb_map": []
    }
def cmd_addideas_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) >= 1:
        raise Exception("no ideas specified")
    if not glob_pc:
        raise Exception("pc not initialized (use initpc or loadpc)")
    
    ideas = args[0]

    for i in ideas:
        glob_pc["ideas"].append(i)
    util.tclog(f"added ideas to pc (use 'showideas' to see them)", 0, locsects)


cmd_addideas_usage = "<idea> [<idea> ...]"
cmd_addideas_desc = "add all <idea>'s to a pending package configuration"

"""
returns list of ideas obtained from specified ideas file
"""
def load_ideas_file(ideas_file):
    out = []
    with open(ideas_file, "r") as fl:
        while True:
            idea = fl.readline()
            if idea == "":
                break
            idea = idea.strip()
            out.append(idea)
    return out

def cmd_addfiles_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) >= 1:
        raise Exception("no files specified")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    
    files = args[0]

    for file in files:
        if not os.path.exists(file):
            raise Exception(f"ideas file path {file} doesn't exist")
        ideas = load_ideas_file(file)
        glob_pc["ideas"] += ideas
    util.tclog(f"added ideas from idea files (use 'showideas' to see them)", 0, locsects)


cmd_addfiles_usage = "<file> [<file> ...]"
cmd_addfiles_desc = "add all <file>'s to a pending package configuration"

def cmd_addqueries_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 1:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    cnt = args[0][0]


    for i in range(int(cnt)):
        glob_pc["queries"].append(empty_query())
    showpc(glob_pc)
    util.tclog(f"added queries to pc", 0, locsects)


cmd_addqueries_usage = "<cnt>"
cmd_addqueries_desc = "add <cnt> queries to a pending package configuration"

def cmd_qparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    try:
        if not len(args):
            raise Exception("invalid number of args")
        if not len(args[0]) == 3:
            raise Exception("invalid number of args")
        if not glob_pc:
            raise Exception("pc not initialized (used initpc)")
        idx, param, val = args[0]

        val = coerce_val(param, val, schemas.pkg_config_schema["properties"]["queries"]["items"]["properties"])

        glob_pc["queries"][int(idx)][param] = val
        showpc(glob_pc)
        util.tclog(f"added param {param} with value {val} to query with idx {idx}", 0, locsects)
    except IndexError:
        raise KeyError(f"query with index {idx} doesn't exist yet (use addquery)")


cmd_qparam_usage = "<idx> <param> <val>"
cmd_qparam_desc = "alter parameter _param_ to value _val_ for query with index _idx_ (except for oai parameters, for which qoaiparam is to be used)"


def cmd_qoaiparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 3:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    idx, param, val = args[0]

    # TODO: add param verification
    glob_pc["queries"][int(idx)]["oai_config"][param] = val
    showpc(glob_pc)
    util.tclog(f"added oai param {param} with value {val} to query with idx {idx}", 0, locsects)


cmd_qoaiparam_usage = "<idx> <oaiparam> <val>"
cmd_qoaiparam_desc = "alter oai parameter <oaiparam> to value <val> for query with index <idx>\nTIP: for non-oai parameters use qparam"

def get_schem_sect(sect):
    out = None
    temp = None
    match sect:
        case "pc":
            temp = dict(schemas.pkg_config_schema["properties"])
            del temp["id"]
        case "pcoai":
            temp = dict(schemas.pkg_config_schema["properties"]["oai_config_gen"]["properties"])
        case "q":
            temp = dict(schemas.pkg_config_schema["properties"]["queries"]["items"]["properties"])
        case "qoai":
            temp = dict(schemas.pkg_config_schema["properties"]["queries"]["items"]["properties"]["oai_config"]["properties"])
        case "incb":
            temp = dict(schemas.pkg_config_schema["properties"]["queries"]["items"]["properties"]["inp_cb_map"]["properties"])
        case _:
            raise Exception("section '{sect}' not found (run 'help params' or 'params' for help on this issue)")


    out = dict(temp)
    for i in temp:
        if (temp[i]["type"] == "array") or (temp[i]["type"] == "object"):
            del out[i]
    return out

def get_req_sect(sect):
    out = None
    match sect:
        case "pc":
            out = list(schemas.pkg_config_schema["required"])
            out.remove("oai_config_gen")
            out.remove("queries")
            out.remove("ideas")
            out.remove("id")
        case "pcoai":
            out = list()
        case "q":
            out = list(schemas.pkg_config_schema["properties"]["queries"]["items"]["required"])
            out.remove("oai_config")
        case "qoai":
            out = list()
        case "incb":
            out = list(schemas.pkg_config_schema["properties"]["queries"]["items"]["properties"]["inp_cb_map"]["required"])
        case _:
            raise Exception("section '{sect}' not found (run 'help params' or 'params' for help on this issue)")


    return out

def set_pc_param(val, param, sect, idx = None):
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    match sect:
        case "pc":
            glob_pc[param] = val
        case "pcoai":
            glob_pc["oai_config_gen"][param] = val
        case "q":
            if idx == None:
                raise Exception("somehow managed to attempt to modify query \
without providing an index...")
            glob_pc["queries"][idx][param] = val
        case "qoai":
            if idx == None:
                raise Exception("somehow managed to attempt to modify query \
without providing an index...")
            glob_pc["queries"][idx][oai_config][param] = val
        case "incb":
            if idx == None:
                raise Exception("somehow managed to attempt to modify query \
without providing an index...")
            glob_pc["queries"][idx][inp_cb_map][param] = val
        case _:
            raise Exception("section '{sect}' not found (run 'help params' or 'params' for help on this issue)")

def cmd_setparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])
    idx = None
    param = None
    val = None
    sect = None


    if not len(args):
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    
    sect = args[0][0]

    if (sect == "pc") or (sect == "pcoai"):
        if not len(args[0]) == 3:
            raise Exception("invalid number of args")
        param, val = args[0][1:]
    elif (sect == "q") or (sect == "qoai") or (sect == "incb"):
        if not len(args[0]) == 4:
            raise Exception("invalid number of args")
        idx, param, val = args[0][1:]
        idx = int(idx)
        util.tclog(f"idx: {idx}")
    else: 
        raise Exception(f"section '{sect}' not found (run 'help params' or 'params' for help on this issue)")

    schem = get_schem_sect(sect)
    
    try:
        val = coerce_val(param, val, schem)
    except KeyError as e:
        magicstr = "'bc82cb068ef102a1f4e296992e5979ef'"
        if str(e) == magicstr: # magic!
            raise Exception(f"{param} not found in supported parameters for \
section {sect}")


    if idx == None:
        set_pc_param(val, param, sect)
    else:
        set_pc_param(val, param, sect, idx)
    showpc(glob_pc)
    util.tclog(f"successfully set parameter {param} for in section {sect} to \
value {val}", 5000, locsects)


cmd_setparam_usage = "<section>('pc' | 'pcoai' | 'q' | 'qoai' | 'incb') [<index>] <param> <val>"
cmd_setparam_desc = "add value <val> to parameter <param> (to query with index <index> where applicable) to section <section> to the pending package configuration\nTIP:see the output of the 'params' command to"

def cmd_pcoaiparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])


    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 2:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (use initpc)")
    param, val = args[0]

    glob_pc["oai_config_gen"][param] = val
    showpc(glob_pc)
    util.tclog(f"added oai param to pc", 0, locsects)


cmd_pcoaiparam_usage = "<oaiparam> <val>"
cmd_pcoaiparam_desc = "add oai param _oaiparam_ to a pending package configuration"

class prms_list():
    def __init__(self, sect, s_dct, r_lst):
        self.sects = list(str(sect))
        self.s_lst = list()
        self.r_lst = list()

        for i in s_dct:
            if (s_dct[i]["type"] == "object") or (s_dct[i]["type"] == "array"):
                continue
            self.s_lst.append(i)
        for i in r_lst:
            self.r_lst.append(i)
    def __iadd__(self, val):
        self.sects += val.sects
        self.s_lst += val.s_lst
        self.r_lst += val.r_lst
        return self
"""
Following two funcs return objects of following form:
"""
def get_prms(sect = None):
    out = None
    
    out = prms_list(sect, get_schem_sect(sect), get_req_sect(sect))

    return out
def cmd_params_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])
    outstr = ""
    prms = None


    if len(args):
        if not len(args[0]) == 1:
            raise Exception("invalid number of args")
        sect = args[0][0]
    else:
        sect = None

    if sect != None:
        outstr = f"parameters for sect {sect}:\n"
        prms = get_prms(sect)
    else:
        outstr = f"all parameters:\n"
        cmd_params_fnc(["pc"])
        cmd_params_fnc(["pcoai"])
        cmd_params_fnc(["q"])
        cmd_params_fnc(["qoai"])
        return

    outstr += "SUPPORTED:\n"
    for i in prms.s_lst:
        outstr += f"{i}\n"
    if len(prms.r_lst):
        outstr += "\nREQUIRED:\n"
        for i in prms.r_lst:
            outstr += f"{i}\n"

    util.tclog(outstr, 0, locsects)
    



cmd_params_usage = "[<section>('pc' | 'pcoai' | 'q' | 'qoai')]"
cmd_params_desc = "shows all possible pc params for section <section> if \
specified, and all sections if unspecified\nsections are as follows:\n\npc - \
general parameters\npcoai - general oai parameters\nq - query parameters for a \
particular query\nqoai - oai parameters for a particular query\nicb - input \
callbacks for a particular query.\n\nAbout input callbacks: it is best to begin \
with an example:\n\nSuppose the prompt for query A is 'list five $i' and the \
prompt for query B is 'generate an exceedingly funny joke about each of the \
following: $0'.\n\nQuery A inserts the original idea into the prompt every time \
it is run, and query B takes the output of query A and inserts it to the end of \
the prompt. Now suppose for some reason query A gives its output as a \
newline-terminated list, but that messes somehow with the responses from query B \
\n\nWhat we could do when faced with such a problem is define a function in \
'tag/tag/proc.py' (see the example function below) and then assign it as \
an input callback for query B. Here's how that would look like in practice:\n\n\
1. Define a function in 'tag/tag/procedures.py':\n\ndef cool_procedure(inp):\n   return inp.replace('\\n', ',')\n\
\n2. With the pc loaded, assign that callback to the input \n\n'pcparam incb 1 0 \
cool_procedure'\n\nThis command defines, for query B (with index 1) the input \
callback (cool_procedure) for working with input from query A (with index 0)\n\n\
Voila! Now when query B gathers input from query A, it will \
first format it with cool_procedure(), replacing all the newlines with commas"



def cmd_clrparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])


    if not len(args):
        raise Exception("invalid number of args")

    if not len(args[0]) >= 2:
        raise Exception("invalid number of args")
    sect, param = args[0]
    
    if sect.startswith("q"):
        if not len(args[0]) == 3:
            raise Exception("invalid number of args")
        idx = args[0][2]
    else:
        if not len(args[0]) == 2:
            raise Exception("invalid number of args")

    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    try:
        match sect:
            case "pc":
                del glob_pc[param]
            case "pcoai":
                del glob_pc["oai_config_gen"][param]
            case "q":
                del glob_pc["queries"][idx][param]
            case "qoai":
                del glob_pc["queries"][idx][oai_config][param]
            case _:
                raise Exception(f"invalid section {sect}")
        showpc(glob_pc)
        util.tclog(f"cleared param '{param}' from pc", 0, locsects)
    except KeyError as e:
        util.tclog(f"param {param} doesn't exist in section {sect}", 0, locsects)

cmd_clrparam_usage = "<section>('pc' | 'pcoai' | 'q' | 'qoai') <param> [<idx>]"
cmd_clrparam_desc = "clear <param> from specified <section>; sections are: pc - general package config param, pcoai - general oai param, q - query param (requires <idx>), qoai - query oai param (requires <idx>)"

def cmd_quit_fnc(*args):
    util.clean_exit(0)


cmd_quit_usage = ""
cmd_quit_desc = "quit TAG-CLI"

def showpc(pc):
    global glob_pc
    locsects = list(util.logsects[__file__])
    sects = ["pc", "pcoai", "q", "qoai"]
    obj = None

    outstr = "LOADED PC PARAMS:\n"

    sect = "pc"

    tempprms = get_prms(sect)
    outstr += f"\nSECT: {sect}\n"
    for prm in tempprms.s_lst:
        if prm in glob_pc:
            outstr += f"{prm}: {glob_pc[prm]}\n"

    outstr += f"END SECT: {sect}\n\n"

    sect = "pcoai"

    tempprms = get_prms(sect)
    outstr += f"SECT: {sect}\n"
    for prm in tempprms.s_lst:
        if prm in glob_pc['oai_config_gen']:
            outstr += f"{prm}: {glob_pc['oai_config_gen'][prm]}\n"
    outstr += f"END SECT: {sect}\n\n"

    outstr += "QUERIES:\n"

    for idx in range(len(glob_pc['queries'])):
        outstr += "----------------\n"

        sect = "q"

        tempprms = get_prms(sect)
        outstr += f"IDX: {idx}\n"
        outstr += f"SECT: {sect}\n"
        for prm in tempprms.s_lst:
            if prm in glob_pc["queries"][idx]:
                outstr += f"{prm}: {glob_pc['queries'][idx][prm]}\n"

        outstr += f"END SECT: {sect}\n\n"
        if len(glob_pc["queries"][idx]["oai_config"]):
            sect = "qoai"

            tempprms = get_prms(sect)
            outstr += f"SECT: {sect}\n"
            for prm in tempprms.s_lst:
                if prm in glob_pc["queries"][idx]:
                    outstr += f"{prm}: {glob_pc['queries'][idx]['oai_config'][prm]}\n"

        # cbs
        if len(glob_pc["queries"][idx]["inp_cb_map"]):
            sect = "icbs"
            outstr += f"SECT: {sect}\n"
            for cbidx in range(len(glob_pc["queries"][idx]["inp_cb_map"])):
                outstr += "****\n"
                outstr += f"input idx: {glob_pc['queries'][idx]['inp_cb_map'][cbidx]['idx']}\n"
                outstr += f"callback name: {glob_pc['queries'][idx]['inp_cb_map'][cbidx]['cb_name']}\n"
            outstr += "****\n"
            outstr += f"END SECT: {sect}\n\n"


    outstr += "----------------\n"

    outstr += "END QUERIES\n"


    util.tclog(outstr, 0, locsects)


def cmd_showpc_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    showpc(glob_pc)
    util.tclog(f"TIP: use 'showideas' to see currently loaded ideas", 0, locsects)


cmd_showpc_usage = ""
cmd_showpc_desc = "show info about pending pc"

def cmd_clearpc_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    glob_pc = None
    
    util.tclog(f"cleared pc", 0, locsects)


cmd_clearpc_usage = ""
cmd_clearpc_desc = "clear pending pc (requires another call to initpc)"

def delete_pcs(pkg_ids):
    for pkg_id in pkg_ids:
        msg = {
            "type": "remove_pkg_config",
            "data": {
                "id": pkg_id
            }
        }
        ipccli.send_dict(msg)
def delete_runs(run_ids):
    for run_id in run_ids:
        msg = {
            "type": "remove_pkg_run",
            "data": {
                "run_id": run_id
            }
        }
        ipccli.send_dict(msg)

def cmd_delete_fnc(*args):
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    elif not len(args[0]) >= 2:
        raise Exception("invalid number of args")


    target = args[0][0]
    ids = args[0][1:]
    match target:
        case "runs":
            delete_runs(ids)
        case "pcs":
            delete_pcs(ids)
        case _:
            raise Exception(f"invalid target '{target}'")


cmd_delete_usage = "<target> <id/run_id> [<id/run_id> ...]"
cmd_delete_desc = "delete saved pcs/runs (as specified in <target> with values \"pcs\" or \"runs\" respectively) with ids/run_ids <id/run_id> [<id> ...] from TAG\nTIP: obtain the id from the pkg name using the `pcs` or `pcid` commands"

def pcs():
    msg = {
        "type": "all_pkg_configs",
        "data": {}
    }
    ipccli.send_dict(msg)

def cmd_listpcsfnc(*args):
    locsects = list(util.logsects[__file__])

    util.tclog("submitting call to get saved pcs...")
    pcs()
    


cmd_listpcsusage = ""
cmd_listpcsdesc = "get a list of all saved pcs"

def pcids(names):
    msg = {
        "type": "get_pkg_ids",
        "data": {
            "names": names 
        }
    }
    ipccli.send_dict(msg)

def cmd_pcids_fnc(*args):
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) >= 1:
        raise Exception("invalid number of args")

    names = args[0]
    pcids(names)
    


cmd_pcids_usage = "<name> [<name> ...]"
cmd_pcids_desc = "get the ids of a packages with names <name> [<name> ...]"

def getpcs(ids):
    msg = {
        "type": "get_pkg_configs",
        "data": {
            "ids": ids 
        }
    }
    ipccli.send_dict(msg)

def cmd_getpcs_fnc(*args):
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) >= 1:
        raise Exception("invalid number of args")

    ids = args[0]
    getpcs(ids)
    


cmd_getpcs_usage = "<id> [<id> ...]"
cmd_getpcs_desc = "get the details of packages with ids <id> [<id> ...]"

def start(pkg_id):
    msg = {
        "type": "start",
        "data": {
            "id": pkg_id
        }
    }
    ipccli.send_dict(msg)

def cmd_start_fnc(*args):
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 1:
        raise Exception("invalid number of args")

    pkg_id = args[0][0]

    start(pkg_id)
    


cmd_start_usage = "<id>"
cmd_start_desc = "start package with id <id>"

def pause():
    msg = {
        "type": "pause",
        "data": {}
    }
    ipccli.send_dict(msg)

def cmd_pause_fnc(*args):
    pause()
    
cmd_pause_usage = ""
cmd_pause_desc = "pause currently running package"

def resume():
    msg = {
        "type": "resume",
        "data": {}
    }
    ipccli.send_dict(msg)

def cmd_resume_fnc(*args):
    resume()
    
cmd_resume_usage = ""
cmd_resume_desc = "resume currently running package"

def rerun(run_id):
    msg = {
        "type": "revive",
        "data": {
            "run_id": run_id
        }
    }
    ipccli.send_dict(msg)
def cmd_rerun_fnc(*args):
    if not len(args):
        raise Exception("invalid number of args")
    run_id = args[0][0]
    rerun(run_id)

cmd_rerun_usage = "<run_id>"
cmd_rerun_desc = "rerun previously run package with run id <run_id>\nTIP: use runs to list previously run packages"


def cancelpc(run_id = None):
    if run_id == None:
        msg = {
            "type": "cancel",
            "data": {}
        }
        ipccli.send_dict(msg)
    else:
        msg = {
            "type": "cancel",
            "data": {"run_id": run_id}
        }
        ipccli.send_dict(msg)

def cmd_cancel_fnc(*args):
    if not len(args):
        cancelpc()
    elif not len(args[0]) == 1:
        raise Exception("invalid number of args")
    run_id = argv[0][0]
    cancelpc(run_id)
    
cmd_cancel_usage = "[<run_id>]"
cmd_cancel_desc = "cancel currently running package (with id <run_id> if provided)"

def listruns():
    msg = {
        "type": "all_runs",
        "data": {}
    }
    ipccli.send_dict(msg)

def cmd_listruns_fnc(*args):
    listruns()
    
cmd_listruns_usage = ""
cmd_listruns_desc = "lists runs (successful, unsuccessful and pending) of pcs"

def showrun(run_id):
    msg = {
        "type": "get_pkg_run",
        "data": {"run_id": run_id}
    }
    ipccli.send_dict(msg)

def cmd_getrun_fnc(*args):
    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 1:
        raise Exception("invalid number of args")
    run_id = args[0][0]
    showrun(run_id)
    
cmd_getrun_usage = "<run_id>"
cmd_getrun_desc = "loads run with id <run_id> up for view"

def cmd_pcoaiparam_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])


    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 2:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    param, val = args[0]

    glob_pc["oai_config_gen"][param] = val
    showpc(glob_pc)
    util.tclog(f"added oai param to pc", 0, locsects)


cmd_pcoaiparam_usage = "<oaiparam> <val>"
cmd_pcoaiparam_desc = "add oai param <oaiparam> to a pending package configuration"

def setkey(key):
    msg = {
        "type": "set_key",
        "data": {
            "key": key
        }
    }
    ipccli.send_dict(msg)

def cmd_setkey_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])


    if not len(args):
        raise Exception("invalid number of args")
    if len(args[0]) != 1:
        raise Exception("invalid number of args")
    key = args[0][0]
    setkey(key)



cmd_setkey_usage = "<oaiparam> <val>"
cmd_setkey_desc = "add oai param <oaiparam> to a pending package configuration"

def loadpc(pkg_id):
    msg = {
        "type": "get_pkg_config",
        "data": {
            "id": pkg_id
        }
    }
    ipccli.send_dict(msg)
def cmd_loadpc_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])


    if not len(args):
        raise Exception("invalid number of args")
    if len(args[0]) != 1:
        raise Exception("invalid number of args")
    if glob_pc:
        raise Exception("another pc is already loaded\nTIP: use clearpc to clear the worked-on pc (this may discard progress)")

    pkg_id = int(args[0][0])
    loadpc(pkg_id)



cmd_loadpc_usage = "<oaiparam> <val>"
cmd_loadpc_desc = "add oai param <oaiparam> to a pending package configuration"

def tag_status():
    msg = {
        "type": "status",
        "data": {}
    }
    ipccli.send_dict(msg)

def cmd_status_fnc(*args):
    tag_status()



cmd_status_usage = ""
cmd_status_desc = "print the current status of the TAG backend"

def purge_runs():
    msg = {
        "type": "clear_pkg_runs",
        "data": {}
    }
    ipccli.send_dict(msg)
def purge_pcs():
    msg = {
        "type": "clear_pkg_configs",
        "data": {}
    }
    ipccli.send_dict(msg)
def cmd_purge_fnc(*args):
    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 1:
        raise Exception("invalid number of args")
    target = args[0][0]
    match target:
        case "runs":
            purge_runs()
        case "pcs":
            purge_pcs()
        case _:
            raise Exception(f"invalid target '{target}'")

cmd_purge_usage = "<target>"
cmd_purge_desc = "clear all saved data about <target>, which can be \"runs\" or \"pcs\""


def cmd_default_fnc():
    global glob_pc
    locsects = list(util.logsects[__file__])

    cmd_initpc_fnc()

    cmd_setparam_fnc(["pc", "overwrite", "True"])
    cmd_setparam_fnc(["pc", "max_failures", 50])

    cmd_setparam_fnc(["pcoai", "model", "text-davinci-003"])
    cmd_setparam_fnc(["pcoai", "max_tokens", 1024])
    cmd_setparam_fnc(["pcoai", "temperature", 0.5])
    cmd_setparam_fnc(["pcoai", "top_p", 1])
    cmd_setparam_fnc(["pcoai", "frequency_penalty", 1])
    cmd_setparam_fnc(["pcoai", "presence_penalty", 1])

    cmd_addqueries_fnc([15])

    cmd_setparam_fnc(["q", 0, "prompt", "Rewrite this title to be more viral and interesting: $i"])
    cmd_setparam_fnc(["q", 0, "out_header", "Rewritten Title"])

    cmd_setparam_fnc(["q", 1, "prompt", "Write an outline for the following title: $0"])
    cmd_setparam_fnc(["q", 1, "out_header", "Article Outline"])

    cmd_setparam_fnc(["q", 2, "prompt", "Generate the top 6 keywords for the following article: $1"])
    cmd_setparam_fnc(["q", 2, "out_header", "Keywords"])

    cmd_setparam_fnc(["q", 3, "prompt", "Generate the top 6 hashtags for the following article: $1"])
    cmd_setparam_fnc(["q", 3, "out_header", "Hashtags"])

    cmd_setparam_fnc(["q", 4, "prompt", "Generate the top 6 wordpress tags for the following article: $1"])
    cmd_setparam_fnc(["q", 4, "out_header", "Wordpress Tags"])

    cmd_setparam_fnc(["q", 5, "prompt", "Write a 160 character wordpress meta-description for the following article: $1"])
    cmd_setparam_fnc(["q", 5, "out_header", "Wordpress Meta Description"])

    cmd_setparam_fnc(["q", 6, "prompt", "Write an Instagram post promoting the following article: $1"])
    cmd_setparam_fnc(["q", 6, "out_header", "Instagram Post"])

    cmd_setparam_fnc(["q", 7, "prompt", "Write a Twitter tweet promoting the following article: $1"])
    cmd_setparam_fnc(["q", 7, "out_header", "Twitter Tweet"])

    cmd_setparam_fnc(["q", 8, "prompt", "Write a Facebook post promoting the following article: $1"])
    cmd_setparam_fnc(["q", 8, "out_header", "Facebook Post"])

    cmd_setparam_fnc(["q", 9, "prompt", "Write a Youtube video description promoting the following article: $1"])
    cmd_setparam_fnc(["q", 9, "out_header", "Youtube Video Description"])

    cmd_setparam_fnc(["q", 10, "prompt", "Write a short Youtube subscribe now and click the notification bell call to action for the following article: $1"])
    cmd_setparam_fnc(["q", 10, "out_header", "Youtube Video CTA"])

    cmd_setparam_fnc(["q", 11, "prompt", "Write a website and sign up on the website for more information call to action promoting the following article: $1"])
    cmd_setparam_fnc(["q", 11, "out_header", "Website CTA"])

    cmd_setparam_fnc(["q", 12, "prompt", "Write a 180 to 220 word Youtube Shorts Script for the following article: $1"])
    cmd_setparam_fnc(["q", 12, "out_header", "Youtube Shorts Script"])

    cmd_setparam_fnc(["q", 13, "prompt", "Write a 10 to 15 word Youtube Shorts subscribe now and notification bell call to action for the following article: $1"])
    cmd_setparam_fnc(["q", 13, "out_header", "Youtube Shorts CTA"])

    cmd_setparam_fnc(["q", 14, "prompt", "Write an introduction for the following article: $1"])
    cmd_setparam_fnc(["q", 14, "out_header", "Introduction"])

    showpc(glob_pc)
    util.tclog(f"default pc initialized\n\n(remember to set the required parameters (see \"params\")))", 0, locsects)

cmd_default_usage = ""
cmd_default_desc = "generate a default pc"

def cmd_showideas_fnc(*args):
    locsects = list(util.logsects[__file__])
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")

    outstr = "IDEAS FOR CURRENTLY LOADED PC:\n"
    for i in glob_pc["ideas"]:
        outstr += f"{i}\n"
    util.tclog(outstr, 0, locsects)


cmd_showideas_usage = ""
cmd_showideas_desc = "show ALL currently added ideas"

def cmd_seticb_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])

    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 3:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    qidx, inp_qidx, cb_name = args[0]

    inp_qidx = int(inp_qidx)
    qidx = int(qidx)

    try: #fingers crossed
        cmd_clricb_fnc([qidx, inp_qidx])
    except Exception as e:
        pass

    temp = {"idx": inp_qidx, "cb_name":cb_name}
    glob_pc["queries"][qidx]["inp_cb_map"].append(temp)
    showpc(glob_pc)
    util.tclog(f"added input callback ({cb_name}) to query ({qidx}) for input from query ({inp_qidx})", 0, locsects)



cmd_seticb_usage = "<qidx> <inp_qidx> <cb_name>"
cmd_seticb_desc = "add input callback (cb) <cb_name> to query with idx <qidx> which \
will be applied to inputs from query <inp_qidx>\nNOTE: you can specify 1 cb per \
input"

def cmd_setocb_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])
    if not len(args):
        raise Exception("invalid number of args")
    if not len(args[0]) == 2:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    qidx, cb_name = args[0]

    qidx = int(qidx)

    glob_pc["queries"][qidx]["out_cb"] = cb_name

    showpc(glob_pc)
    util.tclog(f"added output callback ({cb_name}) to query ({qidx})", 0, locsects)



cmd_setocb_usage = "<qidx> <cb_name>"
cmd_setocb_desc = "set the output callback <cb_name> for query with index <qidx>\
, which will be applied to its output"

def cmd_clrocb_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])
    if not len(args):
        raise Exception("invalid number of args")
    if len(args[0]) != 1:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    qidx = args[0][0]

    qidx = int(qidx)

    del glob_pc["queries"][qidx]["out_cb"]

    showpc(glob_pc)
    util.tclog(f"cleared out_cb for loaded pc", 0, locsects)



cmd_clrocb_usage = "<qidx>"
cmd_clrocb_desc = "Clear output callback for query with idx <qidx> "

def cmd_clricb_fnc(*args):
    global glob_pc
    locsects = list(util.logsects[__file__])
    temp = None
    found = False


    if not len(args):
        raise Exception("invalid number of args")
    if len(args[0]) != 2:
        raise Exception("invalid number of args")
    if not glob_pc:
        raise Exception("pc not initialized (used initpc)")
    qidx, inp_qidx = args[0]

    qidx = int(qidx)
    inp_qidx = int(inp_qidx)

    cbmap = glob_pc["queries"][qidx]["inp_cb_map"]

    for cb in cbmap:
        if cb["idx"] == inp_qidx:
            cbmap.remove(cb)
            found = True
    if found == False:
        raise Exception(f"icb for input from query {inp_qidx} not found in query \
with idx {qidx}")

    showpc(glob_pc)
    util.tclog(f"cleared input callback for query ({qidx}) for input from query \
({inp_qidx})", 0, locsects)



cmd_clricb_usage = "<qidx> <inp_idx>"
cmd_clricb_desc = "For query with idx <qidx>, clear the input callback applied \
to input from query <inp_qidx>"



cmds.append({
    "name": "help", 
    "func": cmd_help_fnc, 
    "usage": cmd_help_usage, 
    "desc": cmd_help_desc,
})
cmds.append({
    "name": "initpc", 
    "func": cmd_initpc_fnc, 
    "usage": cmd_initpc_usage, 
    "desc": cmd_initpc_desc,
})
cmds.append({
    "name": "submit", 
    "func": cmd_submit_fnc, 
    "usage": cmd_submit_usage, 
    "desc": cmd_submit_desc,
})
cmds.append({
    "name": "addideas", 
    "func": cmd_addideas_fnc, 
    "usage": cmd_addideas_usage, 
    "desc": cmd_addideas_desc,
})
cmds.append({
    "name": "addfiles", 
    "func": cmd_addfiles_fnc, 
    "usage": cmd_addfiles_usage, 
    "desc": cmd_addfiles_desc,
})
cmds.append({
    "name": "addqueries", 
    "func": cmd_addqueries_fnc, 
    "usage": cmd_addqueries_usage, 
    "desc": cmd_addqueries_desc,
})
cmds.append({
    "name": "setparam", 
    "func": cmd_setparam_fnc, 
    "usage": cmd_setparam_usage, 
    "desc": cmd_setparam_desc,
})
cmds.append({
    "name": "clrparam", 
    "func": cmd_clrparam_fnc, 
    "usage": cmd_clrparam_usage, 
    "desc": cmd_clrparam_desc,
})
cmds.append({
    "name": "quit", 
    "func": cmd_quit_fnc, 
    "usage": cmd_quit_usage, 
    "desc": cmd_quit_desc,
})
cmds.append({
    "name": "showpc", 
    "func": cmd_showpc_fnc, 
    "usage": cmd_showpc_usage, 
    "desc": cmd_showpc_desc,
})
cmds.append({
    "name": "clearpc", 
    "func": cmd_clearpc_fnc, 
    "usage": cmd_clearpc_usage, 
    "desc": cmd_clearpc_desc,
})
cmds.append({
    "name": "delete", 
    "func": cmd_delete_fnc, 
    "usage": cmd_delete_usage, 
    "desc": cmd_delete_desc,
})
cmds.append({
    "name": "listpcs", 
    "func": cmd_listpcsfnc, 
    "usage": cmd_listpcsusage, 
    "desc": cmd_listpcsdesc,
})
cmds.append({
    "name": "pcids", 
    "func": cmd_pcids_fnc, 
    "usage": cmd_pcids_usage, 
    "desc": cmd_pcids_desc,
})
cmds.append({
    "name": "getpcs", 
    "func": cmd_getpcs_fnc, 
    "usage": cmd_getpcs_usage, 
    "desc": cmd_getpcs_desc,
})
cmds.append({
    "name": "start", 
    "func": cmd_start_fnc, 
    "usage": cmd_start_usage, 
    "desc": cmd_start_desc,
})
cmds.append({
    "name": "pause", 
    "func": cmd_pause_fnc, 
    "usage": cmd_pause_usage, 
    "desc": cmd_pause_desc,
})
cmds.append({
    "name": "resume", 
    "func": cmd_resume_fnc, 
    "usage": cmd_resume_usage, 
    "desc": cmd_resume_desc,
})
cmds.append({
    "name": "cancel", 
    "func": cmd_cancel_fnc, 
    "usage": cmd_cancel_usage, 
    "desc": cmd_cancel_desc,
})
cmds.append({
    "name": "listruns", 
    "func": cmd_listruns_fnc, 
    "usage": cmd_listruns_usage, 
    "desc": cmd_listruns_desc,
})
cmds.append({ 
    "name": "getrun", 
    "func": cmd_getrun_fnc, 
    "usage": cmd_getrun_usage, 
    "desc": cmd_getrun_desc,
})
cmds.append({
    "name": "params", 
    "func": cmd_params_fnc, 
    "usage": cmd_params_usage, 
    "desc": cmd_params_desc,
})
cmds.append({
    "name": "setkey", 
    "func": cmd_setkey_fnc, 
    "usage": cmd_setkey_usage, 
    "desc": cmd_setkey_desc,
})
cmds.append({
    "name": "loadpc", 
    "func": cmd_loadpc_fnc, 
    "usage": cmd_loadpc_usage, 
    "desc": cmd_loadpc_desc,
})
cmds.append({
    "name": "status", 
    "func": cmd_status_fnc, 
    "usage": cmd_status_usage, 
    "desc": cmd_status_desc,
})
cmds.append({
    "name": "rerun", 
    "func": cmd_rerun_fnc, 
    "usage": cmd_rerun_usage, 
    "desc": cmd_rerun_desc,
})
cmds.append({
    "name": "purge", 
    "func": cmd_purge_fnc, 
    "usage": cmd_purge_usage, 
    "desc": cmd_purge_desc,
})
cmds.append({
    "name": "default", 
    "func": cmd_default_fnc, 
    "usage": cmd_default_usage, 
    "desc": cmd_default_desc,
})
cmds.append({
    "name": "showideas", 
    "func": cmd_showideas_fnc, 
    "usage": cmd_showideas_usage, 
    "desc": cmd_showideas_desc,
})
cmds.append({
    "name": "seticb", 
    "func": cmd_seticb_fnc, 
    "usage": cmd_seticb_usage, 
    "desc": cmd_seticb_desc,
})
cmds.append({
    "name": "setocb", 
    "func": cmd_setocb_fnc, 
    "usage": cmd_setocb_usage, 
    "desc": cmd_setocb_desc,
})
cmds.append({
    "name": "clrocb", 
    "func": cmd_clrocb_fnc, 
    "usage": cmd_clrocb_usage, 
    "desc": cmd_clrocb_desc,
})
cmds.append({
    "name": "clricb", 
    "func": cmd_clricb_fnc, 
    "usage": cmd_clricb_usage, 
    "desc": cmd_clricb_desc,
})
