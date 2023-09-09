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
from randeli.cmds import augment

configobj.DEFAULTSECT = "global"
logging.config.dictConfig( randeli.LOGGING )

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

@click.command("map-fonts", short_help="Create fonts.map from installed fonts")
@click.option(
    '--font-map-file',
        'font_file',
        metavar="FILE",
        type=click.Path(),
    help="Save font mapping to FILE", default="fonts.json")
@click.option(
    '--font-dir',
        'font_dir',
        metavar="DIR",
        type=click.Path(exists=True),
        help="Parse fonts rooted at DIR",
        required=True,
        multiple=True)
@click.option(
    '--fallback-font',
        'fallback_font',
        default="CMU Serif",
        metavar="NAME",
        help="Font NAME if font can't be founf mapping" )
@click.option(
    '--computer-modern',
        'cm_alias',
        metavar="NAME",
        default="CMU",
        help="Alias 'Computer Modern' to NAME")
@click.option(
    '--update-config',
        'update_config',
        is_flag=True,
        help="Add specified font-map-file into configuration file")
@click.pass_context
def cli(ctx, font_file, font_dir, fallback_font, cm_alias, update_config ):
    """Build a font map from querying each DIR"""

    from fontTools import ttLib

    fonts = {}

    for dir_ in font_dir:

        LOGGER.info(f"Mapping files under {dir_}")

        for root, dirs, files in os.walk(dir_):
            for filename in files:

                path_to_font = pathlib.PurePosixPath(root, filename)

                if path_to_font.suffix in [".ttf", ".otf", ".ttc" ]:
                    try:
                        font_list = [ ttLib.TTFont(str(path_to_font)) ]
                    except ttLib.TTLibFileIsCollectionError:
                        font_list = ttLib.TTCollection(str(path_to_font))

                    for font in font_list:

                        family_name = str( font['name'].getDebugName(1) )
                        style_name = str( font['name'].getDebugName(2) )

                        if family_name not in fonts:
                            fonts[ family_name ] = {}

                        # Computer Modern's license requires changing the font name for different formats
                        # (i.e. TeX vs Type1)
                        if cm_alias in family_name:
                            if "Computer Modern" not in fonts:
                                fonts[ "Computer Modern" ] = {}
                            fonts[ "Computer Modern" ][ style_name ] = str(path_to_font)

                        fonts[ family_name ][ style_name ] = str(path_to_font)

                else:
                    LOGGER.warn(f"{path_to_font} is not a supported font type")

    with open( font_file, "w") as out:
        json.dump(fonts, out, indent=2, sort_keys=True)

    if update_config:    

        abs_font_file = pathlib.PosixPath(font_file).absolute()

        click.echo( f"Updated font-map in configuration file to {write_config_value_to_file( 'policy.font-map-file', str(abs_font_file), ctx.obj['global.cfg'])}" )

        if fallback_font in fonts:
            click.echo( f"Updated fallback-font in configuration file to {write_config_value_to_file( 'policy.fallback-font', fallback_font, ctx.obj['global.cfg'])}" )

