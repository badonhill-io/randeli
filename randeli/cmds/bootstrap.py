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

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

@click.command("bootstrap", short_help="Initialize randeli")
@click.option('--download', is_flag=True, help="Download 3rd party components")
@click.pass_context
def cli(ctx, download):
    """Initialize randeli configuration"""

    ctx.ensure_object(dict)

    cfg_path = pathlib.PosixPath(ctx.obj['global.cfg'])

    ocrdir = pathlib.PosixPath(ctx.obj['top_dir'],'ocr')
    ocrlibdir = ocrdir / "Lib"

    if not cfg_path.exists():

        config = configobj.ConfigObj(infile=None, write_empty_values=True)
        config["global"] = {}
        config["global"]["backend"] = "apryse"
        config["global"]["verbose"] = 10
        config["global"]["devel"] = False
        config["apryse"] = {}
        config["apryse"]["token"] = "NOTSET"
        config["ocr"] = {}
        config["ocr"]["enabled"] = False
        config["ocr"]["engine"] = "apryse"
        config["ocr"]["libdir"] = str(ocrlibdir)

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

