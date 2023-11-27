import json

import click

import randeli
from randeli import LOGGER


class PDFEventHandler:

    def __init__(self, ctx=None, backend=None):
        self.overlay_boxes = []

        self.ctx = ctx
        self.backend = backend

        self.policy = randeli.policy.Rules()
        self.policy.loadRulesFromDict( ctx )

    def beginPageCB(self, msg : randeli.librandeli.notify.BeginPage):

        status = ""

        self.overlay_boxes = []

        if self.ctx['page'] != 0 and self.ctx['page'] != msg.page_number:
            status = "(not selected for updating)"

        click.echo(f"Page {msg.page_number} / {msg.page_count} {status}")
        LOGGER.debug(f"Page {msg.page_number} / {msg.page_count} {status}")

        if self.ctx['ocr.forced'] is True:

            # Process entire page
            if self.ctx['page'] == 0 or self.ctx['page'] == msg.page_number:


                jsn = self.backend.extractTextFromImage(msg,
                                                        out_filename=self.ctx['write'],
                                                        out_dir=self.ctx['augment.write-into'])

                paragraphs = json.loads(jsn)

                opts = {
                    "box-color": self.policy.strong_box_color,
                    "box-height" : self.policy.strong_box_height,
                    "box-shape" : self.policy.strong_box_shape,
                    "dpi" : paragraphs['Page'][0]["dpi"],
                }

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



    def endPageCB(self, msg : randeli.librandeli.notify.EndPage):

        for box in self.overlay_boxes:
            LOGGER.debug(f"writing box @ {int(box['x'])},{int(box['y'])}")
            LOGGER.debug(f"  {box}")
            self.backend.drawBox( msg.writer, msg.builder, box)

    def elementCB(self, msg : randeli.librandeli.notify.Element):

        if self.ctx['page'] != 0 and self.ctx['page'] != msg.page_number:
            #just write out the unmodified object
            if msg.writer:
                LOGGER.debug("Element on page not selected for modification")
                self.backend.writeElement( msg.writer, msg.element )
            return

        if self.ctx['ocr.forced'] is True:
            # just write out each element, augmentation is handled
            # at the page level
            self.backend.writeElement( msg.writer, msg.element )
            return

        if msg.ele_type_str == "text":

            td = self.backend.getTextDetails(msg.element)
            # TODO - roadmap
            # Feels like PDFs are splitting words into multiple elements
            # Can we look at bbox of this word and the next to see if they are
            # close "enough" that they should be considered a single word
            # i.e. no augmentation in the second element.

            LOGGER.debug(f"Processing '{td['text']}'")

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
                            LOGGER.debug(f"tail {t.GetTextString()}")
                        else:
                            LOGGER.debug(f"tail {t.GetType()}")

                        self.backend.writeElement( msg.writer, t )
                else:
                    # write the original element, any other updates are as "overlay"
                    self.backend.writeElement( msg.writer, msg.element )

                if self.policy.use_strong_box:
                    # to avoid co-ordinate clashes mid page, we need to
                    # split the generation of box cordinates from
                    # creating the box - for that we wait until
                    # after all other elements on the page have been
                    # written
                    opts = {
                        "x-scale": self.policy.box_x_scale,
                        "x-offset": self.policy.box_x_offset,
                        "y-scale": self.policy.box_y_scale,
                        "y-offset": self.policy.box_y_offset,
                        "box-color": self.policy.getStrongBoxColor(),
                        "box-height" : self.policy.strong_box_height,
                        "box-shape" : self.policy.strong_box_shape,
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

                    jsn = self.backend.extractTextFromImage(msg,
                                                            out_filename=self.ctx['write'],
                                                            out_dir=self.ctx['augment.write-into'])
                    paragraphs = json.loads(jsn)

                    opts = {
                        "x-scale": imgd['bbox']['width'] / imgd['width'],
                        "x-offset": imgd['bbox']['x'] + self.policy.box_x_offset,
                        "y-scale": imgd['bbox']['height'] / imgd['height'],
                        "y-offset": imgd['bbox']['y'] + self.policy.box_y_offset,
                        "box-color": self.policy.strong_box_color,
                        "box-height" : self.policy.strong_box_height,
                        "box-shape" : self.policy.strong_box_shape,
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
                    LOGGER.warn(f"Image is smaller than configure minimum OCR size; {imgd['width']}x{imgd['height']} vs {self.policy.min_ocr_image_width}x{self.policy.min_ocr_image_height}")


        else:
            # on the selected page, but not an element that needs to be augmented
            LOGGER.debug(f"Not an element to be augmented ({msg.ele_type_str})")
            self.backend.writeElement( msg.writer, msg.element )
