# Copyright (c) 2023 Richard Offer, All rights reserved.

import pathlib

import click

from randeli import LOGGER

# these get written during bootstrap
BOOTSTRAP_KEYS={
    'apryse.pdfa' : {
        "type" : "bool",
        "default" : False
    },
    'augment.keep-files' : {
        "type" : "bool",
        "default" : False
    },
    'augment.write-into' : {
        "type" : "str"
    },
    'ocr.dpi' : {
        "type" : "int",
        "default" : 72
    },
    'ocr.enabled' : {
        "type" : "bool",
        "default" : False
    },
    'ocr.engine' : {
        "type" : "str",
        "default" : "apryse"
    },
    'ocr.libdir' : {
        "type" : "str"
    },
    'ocr.mode' : {
        "type" : "str",
        "default" : "page"
    },
    'ocr.forced' : {
        "type" : "bool",
        "default" : False
    },
}


def augment_pdf(ctx):

    from randeli.cmds.handlers.augment import PDFEventHandler
    from randeli.librandeli.backend import Apryse as BACKEND

    font_map = pathlib.PosixPath( ctx.obj['policy.font-map-file'] )

    if not font_map.exists:
        LOGGER.fatal(f"Could not open font-map file {str(font_map)}")

    options = {
        "apryse-token" : ctx.obj['apryse.token'],
        "apryse-ocr" :  ctx.obj['ocr.enabled'],
        "apryse-libdir" : ctx.obj['ocr.libdir'],
        "keep-files" : ctx.obj['augment.keep-files'],
        "write-into" : ctx.obj['augment.write-into'],
        "dpi" : ctx.obj['ocr.dpi'],
    }

    if ctx.obj['ocr.enabled'] is True and ctx.obj['ocr.engine'] == "apryse":
        options["apryse-ocr"] = True

    if ctx.obj['ocr.mode'] == "page" or ctx.obj['ocr.forced'] is True:

        options["ocr-whole-page"] = True
    else:
        options["ocr-whole-page"] = False

    try:
        backend = BACKEND(options)

        eventH = PDFEventHandler(ctx=ctx.obj, backend=backend)

        backend.notificationCenter().subscribe("BeginPage", eventH.beginPageCB)
        backend.notificationCenter().subscribe("EndPage", eventH.endPageCB)
        backend.notificationCenter().subscribe("ProcessElement", eventH.elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument( read_only=False )

        args = { }
        if ctx.obj['write']:
            args["filename" ] = ctx.obj['write']
        if ctx.obj['apryse.pdfa']:
            args["pdfa" ] = ctx.obj['apryse.pdfa']

        backend.saveDocument( **args )
        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)


def augment_epub(ctx):

    from randeli.cmds.handlers.augment import EPUBEventHandler
    from randeli.librandeli.backend import EPUB as BACKEND

    options = {
        "write-into" : ctx.obj['augment.write-into'],
    }

    try:
        backend = BACKEND(options)

        eventH = EPUBEventHandler(ctx=ctx.obj, backend=backend)

        backend.notificationCenter().subscribe("BeginPage", eventH.beginPageCB)
        backend.notificationCenter().subscribe("EndPage", eventH.endPageCB)
        backend.notificationCenter().subscribe("ProcessElement", eventH.elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument( read_only=False )

        args = { }
        if ctx.obj['write']:
            args["filename" ] = ctx.obj['write']

        backend.saveDocument( **args )
        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)


def print_hints(ctx, param, value):

    if value:
        click.echo("""
Read a PDF/EPUB and write an augment version based on policies.

For PDFs, OCR by default has been tuned for full page images (i.e. scanned
paper documents, such as patents).

This can cause issues if your document is a mix of well formed
text and in-line images, in that case to avoid duplicated
augmentation try:

  `--ocr-mode element`


In either case, if the boxes are drawn at the wrong locations, you might
need to try a different DPI for the OCR mapping to page coordinates, i.e.
  `--ocr-dpi 96`.
""")
        ctx.exit()

@click.command("augment")
@click.option(
    '--read',
    '-i',
        'read_',
        type=click.Path(exists=True),
        metavar="PATH",
        required=True,
        help="Read PDF/EPUB from PATH")
@click.option(
    '--write',
        'write_',
        metavar="PATH",
        type=click.Path(),
        required=False,
        help="Save augmented file to PATH")
@click.option(
    '--write-into',
        'write_dir_',
        metavar="DIR",
        type=click.Path(),
        required=False,
        help="Save augmented file into DIR (same base filename as input)")
@click.option(
    '--page',
        'page',
        type=int,
        help="Only analyse page PAGE",
        default=0)
@click.option(
    '--ocr',
        'enable_ocr',
        is_flag=True,
        default=BOOTSTRAP_KEYS['ocr.enabled']["default"],
        help="Enable OCR (PDF input only)")
@click.option(
    '--force-ocr',
        'force_ocr',
        is_flag=True,
        default=BOOTSTRAP_KEYS['ocr.forced']["default"],
        help="Force (whole page) OCR even if there are text elements")
@click.option(
    '--ocr-engine',
        'ocr_engine',
        type=click.Choice(["apryse"]),
        default=BOOTSTRAP_KEYS['ocr.engine']["default"],
        help="Select OCR Engine")
@click.option(
    '--ocr-mode',
        'ocr_mode',
        type=click.Choice(["page", "element"]),
        default=BOOTSTRAP_KEYS['ocr.mode']["default"],
        help="Select OCR Mode.")
@click.option(
    '--ocr-dpi',
        'ocr_dpi',
        type=int,
        default=BOOTSTRAP_KEYS['ocr.dpi']["default"],
        help="(expert) Tune resolution used in OCR word locations")
@click.option(
    '--override',
        'override',
        metavar="KEY:VALUE",
        help="Override config values for this run",
        multiple=True)
@click.option(
    '--keep',
        'keep_files',
        default=BOOTSTRAP_KEYS['augment.keep-files']["default"],
        is_flag=True,
        help="Keep intermediate image files extracted by OCR")
@click.option(
    '--pdfa',
        'pdfa',
        default=BOOTSTRAP_KEYS['apryse.pdfa']["default"],
        is_flag=True,
        help="Also write a PDF/A file (PDF input only)")
@click.option(
    '--is-epub',
        'is_epub',
        default=False,
        is_flag=True,
        help="Force parsing input as EPUB")
@click.option(
    '--hints',
        is_flag=True,
        default=False,
        callback=print_hints,
        is_eager=True,
        help="Print additional help"
)
@click.pass_context
def cli(ctx, read_, write_, write_dir_, page, enable_ocr, force_ocr, ocr_engine, ocr_mode, ocr_dpi, override, keep_files, pdfa, hints, is_epub ):
    """Write an augmented PDF/EPUB"""

    ctx.obj['input'] = read_
    ctx.obj['page'] = page
    ctx.obj['write'] = write_
    ctx.obj['augment.write-into'] = write_dir_
    ctx.obj['augment.keep-files'] = keep_files

    ctx.obj['ocr.enabled'] = enable_ocr
    ctx.obj['ocr.forced'] = force_ocr
    ctx.obj['ocr.engine'] = ocr_engine
    ctx.obj['ocr.mode'] = ocr_mode
    ctx.obj['ocr.dpi'] = ocr_dpi

    ctx.obj['apryse.pdfa'] = pdfa

    for kv in override:
        s = kv.split("=")
        ctx.obj[s[0]] = s[1]

    inp = pathlib.Path(read_)

    if inp.suffix == ".epub" or is_epub is True:
        augment_epub(ctx)
    elif inp.suffix == ".pdf":
        augment_pdf(ctx)
    else:
        raise Exception(f"Can't determine file type (PDF/EPUB) from filename '{read_}'")
