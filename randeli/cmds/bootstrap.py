import os
import sys
import configobj
import pathlib
import json
import tempfile
import platform
import subprocess

import logging
import logging.config

import zipfile
import requests
import click

import randeli
from randeli.cmds.config import write_config_value_to_file

from randeli.cli import BOOTSTRAP_KEYS as CLI_KEYS
from randeli.cmds.augment import BOOTSTRAP_KEYS as AUGMENT_KEYS

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

@click.command("bootstrap", short_help="Initialize randeli")
@click.option('--download', is_flag=True, help="Download 3rd party components")
@click.pass_context
def cli(ctx, download):
    """Initialize randeli configuration"""

    ctx.ensure_object(dict)

    cfg_path = pathlib.PosixPath(ctx.obj['global.cfg'])

    ocrdir = pathlib.PosixPath(ctx.obj['global.top'],'ocr')
    ocrlibdir = ocrdir / "Lib"

    if not cfg_path.exists():

        config = configobj.ConfigObj(infile=None, write_empty_values=True, indent_type='  ')
        config.initial_comment = [
            "# initially created using randeli bootstrap",
            "# these represent generally useful defaults",
            "# ",
            "# rather than edit this file directly, suggest using",
            "#   randeli config",
            "# i.e.",
            "#   randeli config set apryse.token <API-TOKEN>"

        ]
        config["global"] = {}
        config["apryse"] = {}
        config["augment"] = {}
        config["ocr"] = {}
        config["policy"] = {}

        config.comments["policy"] = [
            "# use_strong_text -> use a bold font to highlight the start of words (dynamic font)",
            "# use_colored_text -> use a color to highlight the start of words (using colored_text_color)",
            "# use_strong_box -> draw a box at start of words (using strong_box_color)",
            "# strong_box_shape -> default is "box", but "overbar" and "underbar" are options",
            "#   set strong_box_height to a non-zero fixed height (i.e. ~4) for overbar/underbar",
        ]

        for k,t in CLI_KEYS.items():

            s = k.split(".")

            if k in ctx.obj:
                config[s[0]][s[1]] = ctx.obj[k]
            else:
                if "default" in CLI_KEYS[k]:
                    config[s[0]][s[1]] = CLI_KEYS[k]["default"]

        for k,t in AUGMENT_KEYS.items():

            s = k.split(".")

            if k in ctx.obj.items():
                config[s[0]][s[1]] = ctx.obj[k]
            else:
                if "default" in AUGMENT_KEYS[k]:
                    config[s[0]][s[1]] = AUGMENT_KEYS[k]["default"]

        if config["apryse"].get("token", "") == "":
            config['apryse']['token'] = "NOTSET"

        policy = randeli.policy.Rules()
        policy.saveRulesToDict(config)

        config.filename = cfg_path

        config.write()

    else:
        click.echo("Configuration file exists, will not create it.")


    if download:

        click.echo("Installing Apryse PDF SDK")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'apryse_sdk', '--extra-index-url=https://pypi.apryse.com'])

        urls = {
            "Darwin" : "https://www.pdftron.com/downloads/OCRModuleMac.zip",
        }

        if platform.system() in urls:

            with tempfile.TemporaryFile() as fd:

                click.echo(f"Downloading {platform.system()}")

                r = requests.get(urls[platform.system()], stream=True)

                total_size = int(r.headers['Content-Length'])

                size = 0
                with click.progressbar(length=total_size,
                       label=f"Downloading {urls[platform.system()]}") as bar:

                    for chunk in r.iter_content(chunk_size=4096):
                        fd.write(chunk)
                        bar.update(size)
                        size = size + 4096

                fd.seek(0)

                click.echo(f"Unpacking download")
                # TODO change locations if permissions fail

                with zipfile.ZipFile(fd, 'r') as zip:
                    zip.extractall(path=str(ocrlibdir.parent))

            # reset permissions on module
            module = pathlib.PosixPath(ocrlibdir / "OCRModule")
            module.chmod(0o755)

            write_config_value_to_file("ocr.libdir", str(ocrlibdir), str(cfg_path))

        else:
            click.error(f"Unsupported platform '{platform.system()}")

