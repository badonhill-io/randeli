#! /usr/bin/env python3
#
# Copyright (c) 2023 Richard Offer, All rights reserved.

# CLI driver for the randeli application


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

configobj.DEFAULTSECT = "global"
randeli.librandeli.setup_extended_log_levels()
logging.config.dictConfig( randeli.LOGGING )

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

TOPDIR = str(pathlib.PosixPath(randeli.__file__).parent)
CFG = os.path.join(
        click.get_app_dir("randeli", force_posix=True),
        'config.ini')

FONTMAP = os.path.join(
        click.get_app_dir("randeli", force_posix=True),
        'fonts.json')

BOOTSTRAP_KEYS = {
    'global.verbose' : {
        "type" : "int",
        "default" : 10
    },
    'global.backend' : {
        "type" : "str",
        "default" : "apryse"
    },
    'global.cfg' : {
        "type" : "str",
        "default" : CFG
    },
    'global.devel' : {
        "type" : "bool",
        "default" : False
    },
    'global.top' : {
        "type" : "str",
        "default" : TOPDIR
    },
    'policy.font-map-file' : {
        "type" : "str",
        "default" : FONTMAP
    },
    'apryse.token' : {
        "type" : "str",
        "default" : "NOTSET"
    },
}


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
        default=CFG )
@click.option(
    '--backend',
        type=click.Choice(["apryse"]),
        default=BOOTSTRAP_KEYS['global.backend']["default"],
        help="Select backend PDF library")
@click.option(
    '--font-map-file', 
        type=click.Path(),
        metavar="FILE",
        default=FONTMAP,
        help="Load font map from FILE"
        )
@click.option(
    '--log-level',
        'log_level',
        metavar="LOGGER=LEVEL",
        help="Override logging level for given logger",
        multiple=True)
@click.option(
    '--apryse-token',
        metavar="TOKEN",
        default="NOTSET",
        help="API Token for Apryse backend")
def cli(ctx, verbose, devel, cfg, backend, font_map_file, log_level, apryse_token):

    if ctx.invoked_subcommand is None:

        r = RandeliCLI()
        click.echo(r.get_help(ctx=ctx))

        click.echo("")
        click.echo("COMMANDS: ")
        cmds = r.list_commands( ctx = ctx) 
        for c in cmds:
            name = c.replace('.py','')
            mod = __import__(f"randeli.cmds.{name}", None, None, ["cli"])
            click.echo( f"  {name:>10} - {mod.cli.__doc__}" )
        click.echo("""
For additional help on a command use

    `randeli <CMD> --help`
or
    `randeli <CMD> --hints`
""")

    ctx.ensure_object(dict)

    ctx.obj['global.top'] = str(pathlib.PosixPath(randeli.__file__).parent)

    cfg_path = pathlib.Path(cfg)

    # load all values from ~/.randeli/config.ini into ctx
    if cfg_path.exists():
        config = configobj.ConfigObj(infile=str(cfg_path), create_empty=True, write_empty_values=True)

        for k,v in config.dict().items():
            for vv in v:
                # parse booleans
                if f"{k}.{vv}" in [ "global.devel", "ocr.enabled", "apryse.pdfa" ]:
                    ctx.obj[f"{k}.{vv}"] = pydantic.parse_obj_as(bool,v[vv])
                else:
                    ctx.obj[f"{k}.{vv}"] = v[vv]

        if config["apryse"].get("token", "") == "NOTSET":
            ctx.obj['apryse.token'] = ""
        else:
            ctx.obj['apryse.token'] = config["apryse"].get("token","")

    ctx.obj['global.devel'] = devel

    #if font_map_file:
    ctx.obj['policy.font-map-file'] = font_map_file

    font_path = pathlib.Path(ctx.obj['policy.font-map-file'])

    if not font_path.exists():
        ctx.obj['policy.font-map-file'] = ""

    if ctx.obj['global.devel'] is False:
        # disable d.* logging
        logging.getLogger("d.devel").setLevel("ERROR")
        logging.getLogger("d.trace").setLevel("ERROR")

    for kv in log_level:
        s = kv.split("=")
        logging.getLogger( s[0] ).setLevel( s[1] )
        
    # overwrite with supplied configs
    if cfg:
        ctx.obj['global.cfg'] = cfg

    ctx.obj['global.backend'] = backend


if __name__ == '__main__':

    cli( obj={} )

