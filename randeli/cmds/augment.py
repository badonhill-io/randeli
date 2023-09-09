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


@click.command("augment", short_help="Write an augmented PDF")
@click.option('--read', '-i', 'read_', type=click.Path(exists=True), required=True)
@click.option('--write', 'write_', metavar="PATH", type=click.Path(), required=False, help="Save augmented file to PATH")
@click.option('--write-dir', 'write_dir_', metavar="DIR", type=click.Path(), required=False, help="Save augmented file into DIR")
@click.option('--page', 'page', type=int, help="Only analyse page PAGE", default=0)
@click.option('--override', 'override', metavar="KEY:VALUE", help="Override config values from CLI", multiple=True)
@click.pass_context
def cli(ctx, read_, write_, write_dir_, page, override ):
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

