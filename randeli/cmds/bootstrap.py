# Copyright (c) 2023 Richard Offer, All rights reserved.

import pathlib
import platform
import subprocess  # nosec: B404
import sys
import tarfile
import tempfile
import zipfile

import click
import configobj
import requests

import randeli
from randeli import LOGGER
from randeli.cli import BOOTSTRAP_KEYS as CLI_KEYS
from randeli.cmds.augment import BOOTSTRAP_KEYS as AUGMENT_KEYS
from randeli.cmds.config import write_config_value_to_file


@click.command("bootstrap", short_help="Initialize randeli")
@click.option('--download', is_flag=True, help="Download 3rd party components")
@click.option('--force', is_flag=True, help="Forcably update configuration file")
@click.pass_context
def cli(ctx, download, force):
    """Initialize randeli configuration"""

    ctx.ensure_object(dict)

    cfg_path = pathlib.PosixPath(ctx.obj['global.cfg'])

    ocrdir = pathlib.PosixPath(ctx.obj['global.top'],'ocr')
    ocrlibdir = ocrdir / "Lib"

    if force or ( not cfg_path.exists() or ( cfg_path.exists() and cfg_path.stat().st_size == 0 ) ):

        config = configobj.ConfigObj(infile=None, write_empty_values=True, indent_type='  ')
        config.initial_comment = [
            "# initially created using randeli bootstrap",
            "# these represent generally useful defaults",
            "# ",
            "# rather than edit this file directly, suggest using",
            "#   randeli config",
            "# i.e.",
            "#   randeli config set --key=apryse.token --value=<API-TOKEN>"
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
            "# strong_box_shape -> default is 'box', but 'overbar' and 'underbar' are options",
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
            config['apryse']['token'] = "NOTSET" # nosec: B105

        policy = randeli.policy.Rules()
        policy.saveRulesToDict(config)

        if ocrlibdir.exists:
            config["ocr"]["libdir"] = str(ocrlibdir)

        config.filename = cfg_path


        config.write()

    else:
        click.echo("Configuration file exists, will not create it.")
        LOGGER.info("Configuration file exists, will not create it.")


    if download:

        click.echo("Installing Apryse PDF SDK")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'apryse_sdk', '--extra-index-url=https://pypi.apryse.com']) # nosec: B603

        urls = {
            "Darwin" : "https://www.pdftron.com/downloads/OCRModuleMac.zip",
            "Linux" : "https://www.pdftron.com/downloads/OCRModuleLinux.tar.gz",
        }

        if platform.system() in urls:

            with tempfile.TemporaryFile() as fd:

                click.echo(f"Downloading {platform.system()}")

                r = requests.get(urls[platform.system()], stream=True) # nosec: B113

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

                if ".tar.gz" in urls[platform.system()]:
                    tar = tarfile.open(fileobj=fd)
                    tar.extractall(path=str(ocrlibdir.parent)) # nosec: B202
                    tar.close()
                else:
                    with zipfile.ZipFile(fd, 'r') as zip:
                        zip.extractall(path=str(ocrlibdir.parent)) # nosec: B202

            # reset permissions on module
            module = pathlib.PosixPath(ocrlibdir / "OCRModule")
            module.chmod(0o755)

            write_config_value_to_file("ocr.libdir", str(ocrlibdir), str(cfg_path))

        else:
            click.error(f"Unsupported platform '{platform.system()}, please consider filing a bug.")
            LOGGER.debug(f"Unsupported platform '{platform.system()}, please consider filing a bug.")
