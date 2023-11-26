import os
import sys
import configobj
import pathlib
import json
import string

import logging
import logging.config

import click

import randeli
from randeli.librandeli.trace import tracer as FTRACE 

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

KEYS={
    'apryse.token' : "str",
}

def inspect_epub(ctx):
    import randeli.librandeli.backend

    def beginSectionCB(msg:randeli.librandeli.notify.BeginPage):
        LOGGER.notice(f"Page {msg.page_number} / {msg.page_count}")
        LOGGER.detail(f"  src = {msg.page}")

    def elementCB(msg:randeli.librandeli.notify.Element):
        LOGGER.notice(f"    {msg.ele_idx} <{msg.ele_type_str}>")
        # msg.element is a tuple of (parent_node,node) 
        if msg.element[1].text and msg.element[1].text[0].isalpha():
            LOGGER.detail(f"      {msg.element[1].text}")

    options = {
    }

    try:
        backend = randeli.librandeli.backend.EPUB(options)

        backend.notificationCenter().subscribe("BeginPage", beginSectionCB)
        backend.notificationCenter().subscribe("ProcessElement", elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument( read_only=True)

        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)
    

def inspect_pdf(ctx):

    # delay importing until needed in case the apryse sdk is not yet installed
    # i.e. pre-bootstrap
    import randeli.librandeli.backend

    @FTRACE
    def beginPageCB(msg:randeli.librandeli.notify.BeginPage):

        bbox = msg.bbox

        LOGGER.notice(f"Page {msg.page_number} / {msg.page_count}")
        LOGGER.detail(f"  Bounding Box {bbox['x1']},{bbox['y1']} {bbox['x2']},{bbox['y2']} )")

    @FTRACE
    def elementCB(msg:randeli.librandeli.notify.Element):

        if ctx.obj['page'] != 0 and  ctx.obj['page'] != msg.page_number:
            return

        bbox = msg.bbox

        LOGGER.info(f"Element {msg.ele_idx} {msg.ele_type_str} ({msg.ele_type}) ( {bbox['x1']},{bbox['y1']} {bbox['x2']},{bbox['y2']} )")

        if msg.ele_type_str == "image":
            img = backend.getImageDetails(msg.element)
            LOGGER.detail(f"  image details = {img}")

        if msg.ele_type_str == "text":
            td = backend.getTextDetails(msg.element)
            LOGGER.detail(f"  text = {td['text']}")
            if ctx.obj['fonts']:
                LOGGER.detail(f"  font = {td['font-family']} (type={td['font-type']})")

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


def print_long_help_and_exit(ctx, param, value):

    if value is True:
        click.echo("""
Inspect the structure of a PDF/EPUB
""")
        ctx.exit()

@click.command("inspect")
@click.option(
    '--read',
    '-i',
        'read_',
        type=click.Path(exists=True),
        required=True)
@click.option(
    '--fonts',
        'fonts',
        is_flag=True,
        help="Print per-element font details",
        default=False)
@click.option(
    '--page',
        'page',
        type=int,
        metavar="NUMBER",
        help="Only inspect page NUMBER",
        default=0)
@click.option(
    '--override',
        'override',
        metavar="KEY:VALUE",
        help="Override config values from CLI",
        multiple=True)
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
        callback=print_long_help_and_exit,
        expose_value=False,
        help="Print additional help",
        is_eager=True)
@click.pass_context
def cli(ctx, read_, fonts, page, override, is_epub):
    """Read a PDF/EPUB and report on its structure"""

    ctx.obj['page'] = page
    ctx.obj['fonts'] = fonts
    ctx.obj['input'] = read_

    for kv in override:
        s = kv.split("=")
        ctx.obj[s[0]] = s[1]

    inp = pathlib.Path(read_)

    if inp.suffix == ".epub" or is_epub is True:
        inspect_epub(ctx)
    elif inp.suffix == ".pdf":
        inspect_pdf(ctx)
    else:
        raise Exception(f"Can't determine file type (PDF/EPUB) from filename '{read_}'")
        
