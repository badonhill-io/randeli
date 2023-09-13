#! /usr/bin/env python3

import os
import sys
import configobj
import pathlib
import json
import pydantic

import logging
import logging.config

import click

import randeli
from randeli.librandeli.trace import tracer as FTRACE 

configobj.DEFAULTSECT = "global"
randeli.librandeli.setup_extended_log_levels()
logging.config.dictConfig( randeli.LOGGING )

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")


cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmds"))


class RandeliCLI(click.Group):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith(".py") and not filename.startswith("_"):
                rv.append(filename)
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__(f"randeli.cmds.{name}", None, None, ["cli"])
        except ImportError:
            return
        return mod.cli

@click.group(cls=RandeliCLI, invoke_without_command=True)
@click.pass_context
@click.option(
    '--verbose',
    '-v',
        type=int,
        help="Set system-wide verbosity")
@click.option(
    '--devel',
        is_flag=True,
        help="Run in development mode (additional logging)")
@click.option(
    '--cfg',
        type=click.Path(),
        required=False,
        help="Path to configuration file",
        default=os.path.join(
            click.get_app_dir("randeli", force_posix=True),
            'config.ini'))
@click.option(
    '--backend',
        type=click.Choice(["apryse"]),
        default="apryse",
        help="Select backend PDF library")
@click.option(
    '--apryse-token',
        help="API Token for Apryse backend")
@click.option(
    '--font-map-file', 
        'font_file',
        type=click.Path(),
        help="Load font map from FILE",
        default="fonts.json")
@click.option(
    '--log-level',
        'log_level',
        metavar="LOGGER:LEVEL",
        help="Override logging level for given logger",
        multiple=True)
def cli(ctx, verbose, devel, cfg, backend, apryse_token, font_file, log_level):

    if ctx.invoked_subcommand is None:

        r = RandeliCLI()
        print(r.get_help(ctx=ctx))

        print("")
        print("COMMANDS: ")
        cmds = r.list_commands( ctx = ctx) 
        for c in cmds:
            name = c.replace('.py','')
            mod = __import__(f"randeli.cmds.{name}", None, None, ["cli"])
            print( f"  {name:>10} - {mod.cli.__doc__}" )

    ctx.ensure_object(dict)

    ctx.obj['top_dir'] = pathlib.PosixPath(randeli.__file__).parent

    cfg_path = pathlib.Path(cfg)

    # load all values from ~/.randeli/config.ini into ctx
    if cfg_path.exists():
        config = configobj.ConfigObj(infile=str(cfg_path), create_empty=True, write_empty_values=True)

        for k,v in config.dict().items():
            for vv in v:
                # parse booleans
                if f"{k}.{vv}" in [ "global.devel", "ocr.enabled" ]:
                    ctx.obj[f"{k}.{vv}"] = pydantic.parse_obj_as(bool,v[vv])
                else:
                    ctx.obj[f"{k}.{vv}"] = v[vv]

        if config["apryse"].get("token", "") == "NOTSET":
            ctx.obj['apryse.token'] = ""
        else:
            ctx.obj['apryse.token'] = config["apryse"].get("token","")

    ctx.obj['global.devel'] = devel

    if font_file:
        ctx.obj['policy.font-map-file'] = font_file

    font_path = pathlib.Path(ctx.obj['policy.font-map-file'])

    if not font_path.exists():
        ctx.obj['policy.font-map-file'] = ""

    if ctx.obj['global.devel'] is False:
        # disable d.* logging
        logging.getLogger("d.devel").setLevel("ERROR")
        logging.getLogger("d.trace").setLevel("ERROR")

    for kv in log_level:
        s = kv.split(":")
        logging.getLogger( s[0] ).setLevel( s[1] )
        
    # overwrite with supplied configs
    if cfg:
        ctx.obj['global.cfg'] = cfg

    if backend:
        ctx.obj['global.backend'] = backend

    if apryse_token:
        ctx.obj['apryse.token'] = apryse_token


if __name__ == '__main__':

    cli( obj={} )

