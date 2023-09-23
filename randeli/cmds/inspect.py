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

LOGGER = logging.getLogger("r.cli")
DEVLOG = logging.getLogger("d.devel")

def print_long_help_and_exit(ctx, param, value):

    if value is True:
        click.echo("""
Inspect the structure of a PDF
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
    '--hints',
        is_flag=True,
        default=False,
        callback=print_long_help_and_exit,
        help="Print additional help",
        expose_value=False,
        is_eager=True)
@click.pass_context
def cli(ctx, read_, fonts, page, override ):
    """Read a PDF and report on its structure"""

    import randeli.librandeli.backend

    ctx.obj['page'] = page
    ctx.obj['fonts'] = fonts
    ctx.obj['input'] = read_

    for kv in override:
        s = kv.split("=")
        ctx.obj[s[0]] = s[1]

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

