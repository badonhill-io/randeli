#! /usr/bin/env python3

import os
import sys
import configparser
import pathlib

import logging
import logging.config

import click

from loguru import logger

import randeli
from randeli.librandeli.trace import tracer as FTRACE 

configparser.DEFAULTSECT = "global"
randeli.librandeli.setup_extended_log_levels()
logging.config.dictConfig( randeli.LOGGING )

@click.group()
@click.pass_context
@click.option('--verbose', '-v', type=int, help="Set system-wide verbosity")
@click.option('--devel', is_flag=True, help="Run in development mode (additional loggin)")
@click.option('--cfg',
    type=click.Path(),
    required=False,
    help="Path to configuration file",
    default=os.path.join(click.get_app_dir("randeli", force_posix=True), 'config.ini'))
@click.option('--backend',
    type=click.Choice(["apryse"]),
    default="apryse",
    help="Select backend PDF library")
@click.option('--apryse-token', help="API Token for Apryse backend")
def cli(ctx, verbose, devel, cfg, backend, apryse_token):

    ctx.ensure_object(dict)

    cfg_path = pathlib.Path(cfg)

    # load default values from ~/.randeli/config.ini
    if cfg_path.exists():
        config = configparser.ConfigParser( allow_no_value=True)
        config.read(cfg_path)
        ctx.obj['backend'] = config.get("global", "backend", fallback="" )
        ctx.obj['verbose'] = config.get("global", "verbose", fallback=10 )
        ctx.obj['devel'] = config.get("global", "devel", fallback=False )
        if config.get("apryse", "token", fallback="") == "NOTSET":
            ctx.obj['apryse-token'] = ""
        else:
            ctx.obj['apryse-token'] = config.get("apryse", "token", fallback="")

        #logging.config.fileConfig( cfg_path )

    ctx.obj['verbose'] = verbose
    ctx.obj['devel'] = devel

    # overwrite with supplied configs
    if cfg:
        ctx.obj['cfg'] = cfg

    if backend:
        ctx.obj['backend'] = backend

    if apryse_token:
        ctx.obj['apryse-token'] = apryse_token

@cli.command()
@click.pass_context
def setup(ctx ):
    """Create the default configuration file"""

    ctx.ensure_object(dict)
    cfg_path = pathlib.Path(ctx.obj['cfg'])
    if not cfg_path.exists():

        config = configparser.ConfigParser( allow_no_value=True)
        config["global"] = {}
        config["global"]["backend"] = "apryse"
        config["global"]["verbose"] = 10
        config["global"]["verbose"] = 10
        config["apryse"] = {}
        config["apryse"]["token"] = "NOTSET"

        with open( cfg_path, 'w') as configfile:
            config.write(configfile)
    else:
        click.echo("Ignoring setup request; default configuration file exists.")

@cli.command()
@click.option('--key', 'key_', required=True)
@click.option('--value', 'value_', required=False)
@click.pass_context
def config(ctx, key_, value ):
    pass

@cli.command()
@click.option('--read', '-i', 'read_', type=click.Path(exists=True), required=True)
@click.option('--elements', 'elements', is_flag=True, help="Print RLE list of elements", default=False)
@click.option('--sentances', 'sentances', is_flag=True, help="Print IDs of elements that start sentances", default=False)
@click.option('--fonts', 'fonts', is_flag=True, help="Print document font details", default=False)
@click.option('--font-map-file', 'font_file')#, type=click.Path(exists=True), help="Load font map from FILE", default="fonts.json")
@click.option('--page', 'page', type=int, help="Only analyse PAGE number", default=0)
@click.pass_context
def inspect(ctx, read_, elements, sentances, fonts, font_file, page ):

    llog = logging.getLogger("r.cli.inspect")

    llog.error(f"{ctx.obj['backend']} {ctx.obj['apryse-token']}")

    options = {
        "apryse-token" : ctx.obj['apryse-token'],
    }

    try:
        backend = randeli.librandeli.backend.Apryse(options)

        backend.notificationCenter().subscribe("OpenDocument",openDocumentCB)

        backend.loadDocument(read_)
    except Exception as ex:
        llog.exception(str(ex),exc_info=ex)



@FTRACE
def openDocumentCB(msg):

    logging.getLogger("r.cli.inspect").notice(f"in openDocumentCB() payload={msg}")


if __name__ == '__main__':

    cli( obj={} )

