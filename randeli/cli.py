#! /usr/bin/env python3
#
# Copyright (c) 2023 Richard Offer, All rights reserved.

# CLI driver for the randeli application


import os
import pathlib
import sys

import click
import configobj
import pydantic

import randeli
from randeli import LOGGER

configobj.DEFAULTSECT = "global"

TOPDIR = str(pathlib.PosixPath(randeli.__file__).parent)
CFG = os.path.join(
        click.get_app_dir("randeli", force_posix=True),
        'config.ini')

RANDELI_LOG = "randeli.log"

if "RANDELI_CONFIG_PATH" in os.environ:
    CFG = os.environ[ "RANDELI_CONFIG_PATH" ]

if "RANDELI_LOG" in os.environ:
    RANDELI_LOG = os.environ[ "RANDELI_LOG" ]

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
    'global.debug' : {
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
    '--debug',
        is_flag=True,
        help="Run in debug mode (additional logging)")
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
        help="Load font map from FILE"
        )
@click.option(
    '--enable-logger',
        'logger_name',
        type=click.Choice([
            "randeli.cmds.augment",
            "randeli.cmds.bootstrap",
            "randeli.cmds.config",
            "randeli.cmds.inspect",
            "randeli.cmds.handlers.augment.epubeventhandler",
            "randeli.cmds.handlers.augment.pdfeventhandler",
            "randeli.librandeli.backend.apryse",
            "randeli.librandeli.backend.base",
            "randeli.librandeli.backend.epub",
            "randeli.librandeli.notify",
            "randeli.policy.rules",
        ]),
    metavar="LOGGER",
    help="Enable (internal) logger",
    multiple=True)
@click.option(
    '--apryse-token',
        metavar="TOKEN",
        default="NOTSET",
        help="API Token for Apryse backend")
def cli(ctx, verbose, debug, cfg, backend, font_map_file, logger_name, apryse_token):

    LOGGER.enable("randeli.cli")

    if debug is True:

        def stderr_info_filter(record):
            if record["extra"].get("info_only"):
                return record["level"].no == logger.level("INFO").no
            return True

        # remove default (SUCCESS) logger, and re-install it at INFO level
        LOGGER.remove()
        LOGGER.add( RANDELI_LOG, format= "{time:HH:mm:ss} | {name: >33} | {level: <7} | {file:>10}#{line:<3} | {message}", level="DEBUG")
        LOGGER.add( sys.stderr, format ="{time:HH:mm:ss} | {level: ^7} | {message}", colorize=True, level = "INFO" ),

        LOGGER.enable("randeli.cli")
        LOGGER.enable("randeli.cmds.augment")
        LOGGER.enable("randeli.cmds.bootstrap")
        LOGGER.enable("randeli.cmds.config")
        LOGGER.enable("randeli.cmds.inspect")
        LOGGER.enable("randeli.cmds.map-fonts")
        LOGGER.enable("randeli.cmds.handlers.augment.epubeventhandler")
        LOGGER.enable("randeli.cmds.handlers.augment.pdfeventhandler")
        LOGGER.enable("randeli.librandeli.backend.apryse")
        LOGGER.enable("randeli.librandeli.backend.base")
        LOGGER.enable("randeli.librandeli.backend.epub")
        LOGGER.enable("randeli.librandeli.notify")
        LOGGER.enable("randeli.policy.rules")

    for l in logger_name:
        LOGGER.enable(l)

    LOGGER.debug(f"Executing {' '.join(sys.argv)}")

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
    if cfg_path.exists() and cfg_path.stat().st_size != 0:
        config = configobj.ConfigObj(infile=str(cfg_path), create_empty=True, write_empty_values=True)

        for k,v in config.dict().items():
            for vv in v:
                # parse booleans
                if f"{k}.{vv}" in [ "global.debug", "ocr.enabled", "apryse.pdfa" ]:
                    ctx.obj[f"{k}.{vv}"] = pydantic.parse_obj_as(bool,v[vv])
                else:
                    ctx.obj[f"{k}.{vv}"] = v[vv]

        if config["apryse"].get("token", "") == "NOTSET":
            ctx.obj['apryse.token'] = ""
        else:
            ctx.obj['apryse.token'] = config["apryse"].get("token","")

    ctx.obj['global.debug'] = debug

    if font_map_file:
        ctx.obj['policy.font-map-file'] = font_map_file

        font_path = pathlib.Path(ctx.obj['policy.font-map-file'])

        if not font_path.exists():
            ctx.obj['policy.font-map-file'] = ""

    # overwrite with supplied configs
    if cfg:
        ctx.obj['global.cfg'] = cfg

    ctx.obj['global.backend'] = backend


if __name__ == '__main__':

    cli( obj={} ) # pylint: disable=no-value-for-parameter
