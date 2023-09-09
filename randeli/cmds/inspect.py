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

@click.command("inspect", short_help="Inspect the structure of a PDF")
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
        help="Print document font details",
        default=False)
@click.option(
    '--page',
        'page',
        type=int,
        metavar="NUMBER",
        help="Only inspect page NUMBER",
        default=0)
@click.pass_context
def cli(ctx, read_, fonts, page ):
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
