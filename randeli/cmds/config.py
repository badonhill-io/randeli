import os
import sys
import configobj
import pathlib
import json

import logging
import logging.config

import click

import randeli
from randeli.librandeli.trace import tracer as FTRACE 

configobj.DEFAULTSECT = "global"

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")


def write_config_value_to_file(key, value, file):
    """Write a period-separated key and value to configuration file"""

    config = configobj.ConfigObj(infile=file, create_empty=True, write_empty_values=True)

    k = key.split(".")

    config[k[0]][k[1]] = value

    LOGGER.info(f"Updating stored key {key} = {config[k[0]][k[1]]}")

    config.write()

    return config[k[0]][k[1]]

@click.command("inspect", short_help="Inspect the structure of a PDF")
@click.option('--key', 'key_')
@click.option('--value', 'value_')
@click.argument('verb' )
@click.pass_context
def cli(ctx, key_, value_, verb ):
    """Read and Write configuration values"""

    if verb == "get":
        click.echo(ctx.obj[key_])

    elif verb == "set":

        ctx.obj[key_] = value_

        click.echo( write_config_value_to_file( key_, value_,ctx.obj['global.cfg']) )

    elif verb == "list":

        config = configobj.ConfigObj(infile=ctx.obj['global.cfg'],
                                     create_empty=True,
                                     write_empty_values=True)

        for k,v in ctx.obj.items():
            print(f"{k:>32} = {v}")

    else:
        raise Exception(f"Unknown action '{verb}'")

