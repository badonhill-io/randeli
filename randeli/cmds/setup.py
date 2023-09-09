import os
import sys
import configobj
import pathlib
import json

import logging
import logging.config

import click

import randeli

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

@click.command("setup", short_help="Initialize configuration")
@click.pass_context
def setup(ctx ):
    """Create the default configuration file"""

    ctx.ensure_object(dict)

    cfg_path = pathlib.PosixPath(ctx.obj['global.cfg'])

    if not cfg_path.exists():

        config = configobj.ConfigObj(infile=None, write_empty_values=True)
        config["global"] = {}
        config["global"]["backend"] = "apryse"
        config["global"]["verbose"] = 10
        config["global"]["devel"] = False
        config["apryse"] = {}
        config["apryse"]["token"] = "NOTSET"

        policy = randeli.policy.Rules()
        policy.saveRulesToDict(config)

        config.filename = cfg_path

        config.write()

    else:
        click.echo("Ignoring setup request; default configuration file exists.")
