#! /usr/bin/env python3

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
randeli.librandeli.setup_extended_log_levels()
logging.config.dictConfig( randeli.LOGGING )

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")


def write_config_value_to_file(key, value, file):
    """Write a period-separated key and value to configuration file"""

    config = configobj.ConfigObj(infile=file, create_empty=True, write_empty_values=True)

    k = key.split(".")

    config[k[0]][k[1]] = value

    config.write()

    return config[k[0]][k[1]]


@click.group()
@click.pass_context
@click.option('--verbose', '-v', type=int, help="Set system-wide verbosity")
@click.option('--devel', is_flag=True, help="Run in development mode (additional logging)")
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
@click.option('--font-map-file', 'font_file', type=click.Path(), help="Load font map from FILE", default="fonts.json")
@click.option('--log-level', 'log_level', metavar="LOGGER:LEVEL", help="Override logging level for given logger", multiple=True)
def cli(ctx, verbose, devel, cfg, backend, apryse_token, font_file, log_level):

    ctx.ensure_object(dict)

    cfg_path = pathlib.Path(cfg)

    # load all values from ~/.randeli/config.ini into ctx
    if cfg_path.exists():
        config = configobj.ConfigObj(infile=str(cfg_path), create_empty=True, write_empty_values=True)

        for k,v in config.dict().items():
            for vv in v:
                ctx.obj[f"{k}.{vv}"] = v[vv]

        if config["apryse"].get("token", "") == "NOTSET":
            ctx.obj['apryse.token'] = ""
        else:
            ctx.obj['apryse.token'] = config["apryse"].get("token","")

    if font_file:
        ctx.obj['policy.font-map-file'] = font_file

    font_path = pathlib.Path(ctx.obj['policy.font-map-file'])

    if not font_path.exists():
        ctx.obj['policy.font-map-file'] = ""

    if devel is False:
        # disable d.* logging
        logging.getLogger("d.devel").setLevel("ERROR")
        logging.getLogger("d.trace").setLevel("ERROR")

    for kv in log_level:
        s = kv.split(":")
        logging.getLogger( s[0] ).setLevel( s[1] )
        
    # overwrite with supplied configs
    if cfg:
        ctx.obj['global.cfg'] = cfg

    if backend:
        ctx.obj['global.backend'] = backend

    if apryse_token:
        ctx.obj['apryse.token'] = apryse_token


@cli.command()
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

@cli.command()
@click.option('--key', 'key_')
@click.option('--value', 'value_')
@click.argument('verb' )
@click.pass_context
def config(ctx, key_, value_, verb ):
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


@cli.command()
@click.option('--font-map-file', 'font_file', metavar="FILE", type=click.Path(), help="Save font mapping to FILE", default="fonts.json")
@click.option('--font-dir', 'font_dir', metavar="DIR", type=click.Path(exists=True), help="Parse fonts rooted at DIR", required=True, multiple=True)
@click.option('--fallback-font', 'fallback_font', default="CMU Serif", metavar="NAME", help="Font NAME if font can't be founf mapping" )
@click.option('--computer-modern', 'cm_alias', metavar="NAME", default="CMU", help="Alias 'Computer Modern' to NAME")
@click.option('--update-config', 'update_config', is_flag=True, help="Add specified font-map-file into configuration file")
@click.pass_context
def map_fonts(ctx, font_file, font_dir, fallback_font, cm_alias, update_config ):
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


@cli.command()
@click.option('--read', '-i', 'read_', type=click.Path(exists=True), required=True)
@click.option('--fonts', 'fonts', is_flag=True, help="Print document font details", default=False)
@click.option('--page', 'page', type=int, help="Only analyse page PAGE", default=0)
@click.pass_context
def inspect(ctx, read_, fonts, page ):
    """Read a PDF and report on its structure"""

    ctx.obj['page'] = page
    ctx.obj['fonts'] = fonts
    ctx.obj['input'] = read_

    @FTRACE
    def beginPageCB(msg:randeli.librandeli.notify.BeginPage):

        LOGGER.notice(f"Page {msg.page_number} / {msg.page_count}")

    @FTRACE
    def elementCB(msg:randeli.librandeli.notify.Element):

        if ctx.obj['page'] != 0 and  ctx.obj['page'] != msg.page_number:
            return

        LOGGER.info(f"Element {msg.ele_idx} {msg.ele_type_str} ({msg.ele_type})")

        if msg.ele_type_str == "image":
            img = backend.getImageDetails(msg.element)
            LOGGER.detail(f"  image size = {img['width']} x {img['height']}")

        if msg.ele_type_str == "text":
            td = backend.getTextDetails(msg.element)
            LOGGER.detail(f"  text = {td['text']}")
            if ctx.obj['fonts']:
                LOGGER.detail(f"  font = {td['font-family']}")

            pass

    options = {
        "apryse-token" : ctx.obj['apryse.token'],
    }

    try:
        backend = randeli.librandeli.backend.Apryse(options)

        backend.notificationCenter().subscribe("BeginPage", beginPageCB)
        backend.notificationCenter().subscribe("ProcessElement", elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument()

        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)


@cli.command()
@click.option('--read', '-i', 'read_', type=click.Path(exists=True), required=True)
@click.option('--write', 'write_', metavar="PATH", type=click.Path(), required=False, help="Save augmented file to PATH")
@click.option('--write-dir', 'write_dir_', metavar="DIR", type=click.Path(), required=False, help="Save augmented file into DIR")
@click.option('--page', 'page', type=int, help="Only analyse page PAGE", default=0)
@click.option('--override', 'override', metavar="KEY:VALUE", help="Override config values from CLI", multiple=True)
@click.pass_context
def augment(ctx, read_, write_, write_dir_, page, override ):
    """Read a PDF and augment it based on policies"""

    ctx.obj['input'] = read_
    ctx.obj['page'] = page
    ctx.obj['write'] = write_
    ctx.obj['write_dir'] = write_dir_

    for kv in override:
        s = kv.split("=")
        ctx.obj[s[0]] = s[1]

    policy = randeli.policy.Rules()
    policy.loadRulesFromDict( ctx.obj )

    overlay_boxes = []

    @FTRACE
    def beginPageCB(msg : randeli.librandeli.notify.BeginPage):

        status = ""

        if ctx.obj['page'] != 0 and ctx.obj['page'] != msg.page_number:
            status = "(not selected for updating)"

        LOGGER.notice(f"Page {msg.page_number} / {msg.page_count} {status}")


    @FTRACE
    def endPageCB(msg : randeli.librandeli.notify.EndPage):

        nonlocal overlay_boxes

        for box in overlay_boxes:
            DEVLOG.info(f"writing box {box}")
            backend.drawBox( msg.writer, msg.builder, box)

    @FTRACE
    def elementCB(msg : randeli.librandeli.notify.Element):

        if ctx.obj['page'] != 0 and ctx.obj['page'] != msg.page_number:
            #just write out the unmodified object
            if msg.writer:
                DEVLOG.trace("Element on page not selected for modification")
                backend.writeElement( msg.writer, msg.element )
            return

        # TODO OCR


        if msg.ele_type_str == "text":

            td = backend.getTextDetails(msg.element)

            DEVLOG.info(f"Processing {td['text']}") 

            if policy.shouldMarkup( td['text'] ):
                LOGGER.debug(f"policy will markup {td['text']}")

                splits = policy.splitWord( td['text'] )

                if policy.use_strong_text:

                    opts={
                        "font-path" : policy.getStrongFontPath(td['font-family'],
                                                     italic=td['italic'],
                                                     size=td['font-size']
                                                    ),
                        "font-size": policy.getStrongFontSize(td["font-size"]),
                        "text-color": policy.getStrongTextColor(),
                    }
                
                    head_ele = backend.updateTextInElement(
                        msg.writer, msg.element, splits.head,
                        style=opts)

                    backend.writeElement( msg.writer, head_ele )

                    opts={
                        "font" : td['font'],
                        "font-size": td["font-size"],
                    }
                    tail_ele = backend.newTextElements(msg.element, msg.builder, splits.tail, style=opts)

                    for t in tail_ele:
                        if t.GetType() == 3:
                            DEVLOG.info(f"tail {t.GetTextString()}")
                        else:
                            DEVLOG.info(f"tail {t.GetType()}")

                        backend.writeElement( msg.writer, t )
                else:
                    # write the original element, any other updates are as "overlay"
                    backend.writeElement( msg.writer, msg.element )

                if policy.use_strong_box:
                    # to avoid co-ordinate clashses mid page, we need to
                    # split the generation of box cordinates from
                    # creating the box - for that we wait until
                    # after all other elements on the page have been
                    # written
                    opts = {
                        "box-color": policy.getStrongBoxColor(),
                        "box-height" : policy.strong_box_height,
                        "box-width" : float(len(splits.head) / len(td['text'])) ,
                    }

                    box = backend.newBox( td, style=opts )

                    nonlocal overlay_boxes
                    overlay_boxes.append(box)

            else:
                # shouldMarkup == False
                DEVLOG.info("shouldMarkup==false")
                backend.writeElement( msg.writer, msg.element )

        else:
            # on the selected page, but not an element that needs to be augmented
            DEVLOG.info("Not a text element")
            backend.writeElement( msg.writer, msg.element )


    options = {
        "apryse-token" : ctx.obj['apryse.token'],
    }

    try:
        backend = randeli.librandeli.backend.Apryse(options)

        backend.notificationCenter().subscribe("BeginPage", beginPageCB)
        backend.notificationCenter().subscribe("EndPage", endPageCB)
        backend.notificationCenter().subscribe("ProcessElement", elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument( read_only=False )

        args = { }
        if write_:
            args["filename" ] = ctx.obj['write']
        if write_dir_:
            args["in_dir" ] = ctx.obj['write_dir']

        backend.saveDocument( **args )
        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)


if __name__ == '__main__':

    cli( obj={} )
