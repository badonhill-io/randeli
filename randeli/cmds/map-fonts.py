import json
import os
import pathlib
import platform
import re

import click

from randeli import LOGGER

from .config import write_config_value_to_file

darwin_font_paths=["/Library/Fonts/", "/System/Library/Fonts/", f'{os.environ.get("HOME", "")}/Library/Fonts']
linux_font_paths=["/usr/share/fonts/opentype", "/usr/share/fonts/truetype", "/usr/share/fonts/type1"]
default_font_paths = None

if platform.system() == "Darwin":
    default_font_paths = darwin_font_paths
elif platform.system() == "Linux":
    default_font_paths = linux_font_paths

def print_long_help_and_exit(ctx, param, value):

    if value is True:

        font_dirs = "\n - ".join(default_font_paths)

        click.echo(f"""
Build a font map from querying fonts in each FONTDIR

 - {font_dirs}

Use --alias ALIAS:FONTNAME as a generic font mapper.

i.e. --alias 'LMRoman:Latin Modern'
""")
        ctx.exit()

@click.command("map-fonts")
@click.option(
    '--font-map-file',
        'font_file',
        metavar="FILE",
        type=click.Path(),
        help="Save font mapping to FILE",
        default=os.path.join(
            click.get_app_dir("randeli", force_posix=True),
            'fonts.json'))
@click.option(
    '--font-dir',
        'font_dir',
        metavar="DIR",
        type=click.Path(exists=True),
        help="Parse fonts rooted at DIR",
        default=default_font_paths,
        required=True,
        multiple=True)
@click.option(
    '--fallback-font',
        'fallback_font',
        default="None",
        metavar="NAME",
        help="Font NAME if font can't be found mapping" )
@click.option(
    '--computer-modern',
        'cm_alias',
        metavar="ALIAS",
        default="CMU",
        help="Alias 'Computer Modern' to ALIAS")
@click.option(
    '--update-config',
        'update_config',
        is_flag=True,
        help="Add specified font-map-file into configuration file")
@click.option(
    '--alias',
        'alias',
        metavar="ALIAS:FONTNAME",
        default=["LMRoman:Latin Modern Roman"],
        help="ALIAS aliased to 'FONTNAME'",
        multiple=True)
@click.option(
    '--echo',
        'echo',
        is_flag=True,
        help="Display font names/styles")
@click.option(
    '--hints',
        is_flag=True,
        default=False,
        callback=print_long_help_and_exit,
        expose_value=False,
        is_eager=True)
@click.pass_context
def cli(ctx, font_file, font_dir, fallback_font, cm_alias, update_config, alias, echo):
    """Create fonts.map from installed fonts"""

    from fontTools import ttLib

    fonts = {}

    aliases = []

    for a in alias:
        aliases.append( a )

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

                        # handle Latin Modern Roman which embeds the point size
                        # in the style, i.e.
                        #   [LMRoman][10 Bold]
                        # ->
                        #   [LMRoman10][Bold]

                        match = re.search(r"(\d+) (.+)", style_name)
                        if match:

                            family_name = family_name + match.group(1)
                            style_name = match.group(2)

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
                    LOGGER.warning(f"{path_to_font} is not a supported font type")

    for alias in aliases:

        (to,frm) = alias.split(':')

        for basename, styles in list(fonts.items()):

            if frm in basename:
                alias = basename.replace(frm, to)

                if alias not in fonts:
                    fonts[alias] = {}

                for style, path in styles.items():
                    fonts[alias][style] = path

    sorted_fonts = dict(sorted(fonts.items()))

    def _print_fonts():
        for font,styles in sorted_fonts.items():
            yield f"{font}\n"
            for style,path in styles.items():
                yield f"  {style}\n"

    if echo is True:
        click.echo_via_pager(_print_fonts())

    with open( font_file, "w") as out:

        LOGGER.info(f"Writing font map to {font_file}")

        json.dump(sorted_fonts, out, indent=2, sort_keys=True)

    if update_config is True:

        abs_font_file = pathlib.PosixPath(font_file).absolute()

        click.echo( f"Updated font-map in configuration file to {write_config_value_to_file( 'policy.font-map-file', str(abs_font_file), ctx.obj['global.cfg'])}" )

        if fallback_font in sorted_fonts:
            click.echo( f"Updated fallback-font in configuration file to {write_config_value_to_file( 'policy.fallback-font', fallback_font, ctx.obj['global.cfg'])}" )
