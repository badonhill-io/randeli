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
}

class EventHandler:

    def __init__(self, ctx=None, backend=None):
        self.overlay_boxes = []

        self.ctx = ctx
        self.backend = backend

        self.policy = randeli.policy.Rules()
        self.policy.loadRulesFromDict( ctx )

    @FTRACE
    def beginPageCB(self, msg : randeli.librandeli.notify.BeginPage):

        status = ""

        self.overlay_boxes = []

        if self.ctx['page'] != 0 and self.ctx['page'] != msg.page_number:
            status = "(not selected for updating)"

        LOGGER.notice(f"Page {msg.page_number} / {msg.page_count} {status}")


    @FTRACE
    def endPageCB(self, msg : randeli.librandeli.notify.EndPage):

        for box in self.overlay_boxes:
            DEVLOG.detail(f"writing box @ {int(box['x'])},{int(box['y'])}")
            DEVLOG.debug(f"  {box}")
            self.backend.drawBox( msg.writer, msg.builder, box)

    @FTRACE
    def elementCB(self, msg : randeli.librandeli.notify.Element):

        if self.ctx['page'] != 0 and self.ctx['page'] != msg.page_number:
            #just write out the unmodified object
            if msg.writer:
                DEVLOG.trace("Element on page not selected for modification")
                self.backend.writeElement( msg.writer, msg.element )
            return

        if msg.ele_type_str == "text":

            td = self.backend.getTextDetails(msg.element)
            # TODO - roadmap
            # Feels like PDFs are splitting words into multiple elements
            # Can we look at bbox of this word and the next to see if they are
            # close "enough" that they should be considered a single word
            # i.e. no augmentation in the second element.

            DEVLOG.info(f"Processing '{td['text']}'")

            if self.policy.shouldAugment( td['text'] ):
                LOGGER.debug(f"policy will markup {td['text']}")

                splits = self.policy.splitWord( td['text'] )

                if self.policy.use_strong_text or self.policy.use_colored_text :

                    opts={
                        "font-path" : self.policy.getStrongFontPath(
                            td['font-family'],
                            italic=td['italic'],
                            size=td['font-size']
                        ),
                        "font-size": self.policy.getStrongFontSize(td["font-size"]),
                        "text-color": self.policy.getColoredTextColor(),
                    }

                    head_ele = self.backend.updateTextInElement(
                        msg.writer, msg.element, splits.head,
                        style=opts)

                    self.backend.writeElement( msg.writer, head_ele )

                    opts={
                        "font" : td['font'],
                        "font-size": td["font-size"],
                    }
                    tail_ele = self.backend.newTextElements(msg.element, msg.builder, splits.tail, style=opts)

                    for t in tail_ele:
                        if t.GetType() == 3:
                            DEVLOG.detail(f"tail {t.GetTextString()}")
                        else:
                            DEVLOG.detail(f"tail {t.GetType()}")

                        self.backend.writeElement( msg.writer, t )
                else:
                    # write the original element, any other updates are as "overlay"
                    self.backend.writeElement( msg.writer, msg.element )

                if self.policy.use_strong_box:
                    # to avoid co-ordinate clashses mid page, we need to
                    # split the generation of box cordinates from
                    # creating the box - for that we wait until
                    # after all other elements on the page have been
                    # written
                    opts = {
                        "box-x-scale": self.policy.box_x_scale,
                        "box-x-offset": self.policy.box_x_offset,
                        "box-y-scale": self.policy.box_y_scale,
                        "box-y-offset": self.policy.box_y_offset,
                        "box-color": self.policy.getStrongBoxColor(),
                        "box-height" : self.policy.strong_box_height,
                        "box-width" : float(len(splits.head) / len(td['text'])) ,
                    }

                    box = self.backend.newBox( td, style=opts )

                    self.overlay_boxes.append(box)

            else:
                # shouldAugment == False
                self.backend.writeElement( msg.writer, msg.element )

        elif msg.ele_type_str == "image":
            self.backend.writeElement( msg.writer, msg.element )

            if self.ctx['ocr.enabled'] is True:

                imgd = self.backend.getImageDetails(msg.element)
                LOGGER.debug(f"Image {imgd}")

                if imgd['width'] > self.policy.min_ocr_image_width and imgd['height'] > self.policy.min_ocr_image_height:

                    LOGGER.debug(f"Found image, processing using OCR ({self.ctx['ocr.mode']})")

                    jsn = self.backend.extractTextFromImage(msg, out_filename=self.ctx['write'], out_dir=self.ctx['augment.write-into'])
                    paragraphs = json.loads(jsn)

                    opts = {
                        "img-x-scale": imgd['bbox']['width'] / imgd['width'], #self.policy.box_x_scale,
                        "img-x-offset": imgd['bbox']['x'] + self.policy.box_x_offset,
                        "img-y-scale": imgd['bbox']['height'] / imgd['height'], #self.policy.box_y_scale,
                        "img-y-offset": imgd['bbox']['y'] + self.policy.box_y_offset,
                        "box-color": self.policy.getStrongBoxColor(),
                        # if 0 then look at the word's font-size`
                        "box-height" : self.policy.strong_box_height,
                        "dpi" : paragraphs['Page'][0]["dpi"],
                    }

                    # TODO tidy up interface,
                    # this is exposing Apryse view of extracted text into application code.
                    for p in paragraphs['Page'][0]['Para']:
                        for l in p['Line']:
                            for word_obj in l['Word']:

                                if self.policy.shouldAugment(word_obj['text'],
                                                            words_in_line=len(l['Word']),
                                                            lines_in_para=len(p['Line'])):

                                    splits = self.policy.splitWord( word_obj['text'] )

                                    opts["box-width"] = float(len(splits.head) / len(word_obj['text']))

                                    box = self.backend.newBox( word_obj, style=opts)

                                    self.overlay_boxes.append( box )

                else:
                    LOGGER.warn("Image is smaller than configure minimum OCR size")


        else:
            # on the selected page, but not an element that needs to be augmented
            DEVLOG.info(f"Not an element to be augmented ({msg.ele_type_str})")
            self.backend.writeElement( msg.writer, msg.element )


def print_hints(ctx, param, value):

    if value:
        click.echo("""
Read a PDF and write an augment version based on policies.

OCR by default has been tuned for full page images (i.e. scanned
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
        help="Read PDF from PATH")
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
        help="Enable OCR")
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
        help="Override config values from CLI",
        multiple=True)
@click.option(
    '--keep',
        'keep_files',
        default=BOOTSTRAP_KEYS['augment.keep-files']["default"],
        is_flag=True,
        help="Keep intermediate OCR files")
@click.option(
    '--pdfa',
        'pdfa',
        default=BOOTSTRAP_KEYS['apryse.pdfa']["default"],
        is_flag=True,
        help="Also write a PDF/A file")
@click.option(
    '--hints',
        is_flag=True,
        default=False,
        callback=print_hints,
        is_eager=True,
        help="Print additional help"
)
@click.pass_context
def cli(ctx, read_, write_, write_dir_, page, enable_ocr, ocr_engine, ocr_mode, ocr_dpi, override, keep_files, pdfa, hints ):
    """Write an augmented PDF"""

    import randeli.librandeli.backend

    ctx.obj['input'] = read_
    ctx.obj['page'] = page
    ctx.obj['write'] = write_
    ctx.obj['augment.write-into'] = write_dir_
    ctx.obj['augment.keep-files'] = keep_files

    ctx.obj['ocr.enabled'] = enable_ocr
    ctx.obj['ocr.engine'] = ocr_engine
    ctx.obj['ocr.mode'] = ocr_mode
    ctx.obj['ocr.dpi'] = ocr_dpi

    ctx.obj['apryse.pdfa'] = pdfa

    for kv in override:
        s = kv.split("=")
        ctx.obj[s[0]] = s[1]

    font_map = pathlib.PosixPath( ctx.obj['policy.font-map-file'] )

    if not font_map.exists:
        LOGGER.fatal(f"Could not open {str(font_map)}")

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

    if ctx.obj['ocr.mode'] == "page" :

        options["ocr-whole-page"] = True
    else:
        options["ocr-whole-page"] = False

    try:
        backend = randeli.librandeli.backend.Apryse(options)

        eventH = EventHandler(ctx=ctx.obj, backend=backend)

        backend.notificationCenter().subscribe("BeginPage", eventH.beginPageCB)
        backend.notificationCenter().subscribe("EndPage", eventH.endPageCB)
        backend.notificationCenter().subscribe("ProcessElement", eventH.elementCB)

        backend.loadDocument(ctx.obj['input'])

        backend.processDocument( read_only=False )

        args = { }
        if write_:
            args["filename" ] = ctx.obj['write']
        if ctx.obj['apryse.pdfa']:
            args["pdfa" ] = ctx.obj['apryse.pdfa']

        backend.saveDocument( **args )
        backend.finalise()

    except Exception as ex:
        LOGGER.exception(str(ex),exc_info=ex)

