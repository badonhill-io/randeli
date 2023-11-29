
import math
import tempfile
from pathlib import PosixPath

import apryse_sdk as APRYSE

from randeli import LOGGER

from .. import notify
from .base import BaseDocument

ELEMENTTYPES = {
        0 : "null",
        1 : "path",
        2 : "text-begin",
        3 : "text",
        4 : "new-line",
        5 : "text-end",
        6 : "image",
        7 : "inline-image",
        8 : "shading",
        9 : "form",
        10 : "group-begin",
        11 : "group-end",
        12 : "marked-content-begin",
        13 : "marked-content-end",
        14 : "marked-content-point",
}

class Apryse(BaseDocument):

    def __init__(self, options=None):
        super().__init__(options=options)

        self._document = None

        self._ocr_options = None

        self.fonts = None

        if "apryse-token" not in self.options or self.options["apryse-token"] == "":
            LOGGER.critical("Missing Apryse API key")
            raise Exception("Missing Apryse API key")

        APRYSE.PDFNet.Initialize( self.options["apryse-token"] )

        try:
            if self.options.get("apryse-ocr", False) is True:

                self._ocr_options = APRYSE.OCROptions()
                self._ocr_options.SetUsePDFPageCoords(True)
                self._ocr_options.AddDPI(options["dpi"])

                if self.options.get("apryse-libdir", ""):

                    self._ocrdir = self.options["apryse-libdir"]

                    APRYSE.PDFNet.AddResourceSearchPath(self._ocrdir)
                    LOGGER.info(f"OCR has been enabled")
                    LOGGER.debug(f" libdir = {self._ocrdir}")

                else:
                    LOGGER.error("OCR has been requested, but no ocr.libdir is set")

        except Exception as e:
            LOGGER.exception(str(e))


    def finalise(self):

        self.document.Close()

        APRYSE.PDFNet.Terminate()


    def loadDocument(self, filename=""):
        super().loadDocument(filename)

        self.fonts = {}

        self.document = APRYSE.PDFDoc( self.read_file )

        self.document.InitSecurityHandler()

        self.page_count = self.document.GetPageCount()
        self.page_number = 0

        call_data = notify.OpenDocument(document=self.document,
                                        filename=filename,
                                        page_count=self.document.GetPageCount())

        LOGGER.trace("Posting OpenDocument notification")

        self.notificationCenter().raise_event("OpenDocument", call_data)

        LOGGER.trace("Posted OpenDocument notification")

    def processDocument(self, read_only=True):

        reader = APRYSE.ElementReader()
        writer = None
        builder = None
        if read_only == False:
            writer = APRYSE.ElementWriter()
            builder = APRYSE.ElementBuilder()

        self.page_number = 0

        itr = self.document.GetPageIterator()

        while itr.HasNext():

            self.page_number += 1

            page = itr.Current()

            reader.Begin(page)
            if writer:
                writer.Begin(page, APRYSE.ElementWriter.e_replacement, False)

            rect = page.GetBox( APRYSE.Page.e_media )

            bounding  = {
                "x1" : int(rect.GetX1()),
                "y1" : int(rect.GetY1()),
                "x2" : int(rect.GetX2()),
                "y2" : int(rect.GetY2()),
            }

            begin_page = notify.BeginPage(document=self.document,
                                         page=page,
                                         page_count=self.page_count,
                                         page_number=self.page_number,
                                         bbox=bounding)

            LOGGER.trace("Posting BeginPage notification")
            self.notificationCenter().raise_event("BeginPage", begin_page)

            # reset to zero on each page
            self.ele_index = 0

            self.processPage(reader, writer, builder, page)

            end_page = notify.EndPage(document=self.document, writer=writer, builder=builder)

            LOGGER.trace("Posting EndPage notification")
            self.notificationCenter().raise_event("EndPage", end_page)

            reader.End()
            if writer:
                writer.End()

            itr.Next()

    def processPage(self, reader, writer, builder, current_page):
        super().processPage(reader, writer, builder, current_page)

        page_elements = []

        ele = reader.Next()

        while ele != None:

            self.ele_index += 1

            page_elements.append( ele.GetType() )

            rect = ele.GetBBox()
            bounding  = {
                "x1" : int(rect.GetX1()),
                "y1" : int(rect.GetY1()),
                "x2" : int(rect.GetX2()),
                "y2" : int(rect.GetY2()),
            }

            element = notify.Element(document=self.document,
                                     reader=reader,
                                     writer=writer,
                                     builder=builder,
                                     page=current_page,
                                     page_number=self.page_number,
                                     page_elements=page_elements,
                                     bbox=bounding,
                                     ele_idx=self.ele_index,
                                     ele_type=ele.GetType(),
                                     ele_type_str=ELEMENTTYPES[ele.GetType()],
                                     element=ele,
                                     )

            LOGGER.trace("Posting Element notification")
            self.notificationCenter().raise_event("ProcessElement", element)

            ele = reader.Next()

    def writeElement(self, writer, element):
        if writer and element:
            writer.WriteElement(element)

    def writePlacedElement(self, writer, element):
        if writer and element:
            writer.WritePlacedElement(element)
            writer.Flush()

    def saveDocument(self, filename="", write_into="", pdfa=False):
        # standardize generation of save pathname

        if write_into == "" and self.options['write-into']:
            write_into = self.options['write-into']

        super().saveDocument(filename=filename, in_dir=write_into)


        info = self.document.GetDocInfo()
        producer = info.GetProducer()
        info.SetProducer(f"{producer} - Augmented using 'randeli' by Badon Hill Technologies Ltd. https://github.com/badonhill-io/randeli")
        d = APRYSE.Date()
        d.SetCurrentTime()
        info.SetModDate( d )

        self.document.Save(str(self.save_file), APRYSE.SDFDoc.e_remove_unused )
        LOGGER.success(f"Saved augmented variant of {self.read_file} to {self.save_file.resolve()}")

        if pdfa is True:
            pdfa_file = self.save_file.replace(".pdf", "_PDFA.pdf")


            pdf_a = APRYSE.PDFACompliance(True, self.save_file, None, APRYSE.PDFACompliance.e_Level2B, 0, 10)

            pdf_a.SaveAs(pdfa_file , False)

            LOGGER.success(f"Saved PDF/A to {pdfa_file}")



    def getImageDetails(self, ele=None) -> dict():
        if ele is None:
            return {}
        rect = ele.GetBBox()
        h = ele.GetImageHeight()
        w = ele.GetImageWidth()
        return {
            "width" : w ,
            "height" : h,
            "bbox" : {
                "x" : int(rect.GetX1()),
                "y" : int(rect.GetY1()),
                "width" : int(rect.GetX2() - rect.GetX1()) ,
                "height" : int(rect.GetY2() - rect.GetY1()),
            }
        }

    def getTextDetails(self, ele) -> dict():
        rect = ele.GetBBox()
        txt = ele.GetTextString()
        fnt = ele.GetGState().GetFont()
        font_family = fnt.GetFamilyName() or fnt.GetName()
        name = fnt.GetName() or fnt.GetFamilyName()
        sz = ele.GetGState().GetFontSize()

        self.fonts[(sz,name)] =  fnt

        desc = fnt.GetDescriptor()
        italic = fnt.IsItalic()

        if desc:
            itr = desc.GetDictIterator()
            while itr.HasNext():
                key = itr.Key()
                value = itr.Value()
                if key.GetName() == "ItalicAngle" and not math.isclose( value.GetNumber(), 0.0 ) :
                    italic = True
                itr.Next()

        return {
            "text" : txt,
            "font" : fnt,
            "font-name" : name,
            "font-family" : font_family,
            "italic" : italic,
            "font-size" : sz,
            "font-type" : fnt.GetType(),
            "x" : rect.GetX1(),
            "y" : rect.GetY1(),
            "length" : rect.GetX2() - rect.GetX1(),
            "height" : rect.GetY2() - rect.GetY1(),
        }

    def updateTextInElement(self, writer, ele, txt, style=None) -> object:
        """TODO
        this currently only handles UTF-8 (i.e. pdflatex), it does not
        handle xelatex generated PDFs - the font mapping is different
        (simple vs complex fonts?)
        """

        style = style or {}

        gs = ele.GetGState()

        head_len = len(txt)
        td = ele.GetTextData()
        ele.SetTextData(td[:head_len], len(td[:head_len]) )


        if "font-path" in style and "font-size" in style:

            if style['font-path'] and style['font-size'] > 0.0:

                LOGGER.debug(f"Using {style['font-path']}")

                fnt = APRYSE.Font.CreateTrueTypeFont(
                        self.document.GetSDFDoc(),
                        style["font-path"] )


                LOGGER.debug(f"Using {style['font-path']} @ {style['font-size']} as strong")
                gs.SetFont(fnt, style['font-size'])

            else:
                LOGGER.detail("No font specified in style")

        if "text-color" in style and len(style['text-color']) > 6:
            # text-color is #rrggbbaa string, convert to 0.0->1.0
            rgb = self._txt_to_rgb(style['text-color'])

            gs.SetFillColorSpace(APRYSE.ColorSpace.CreateDeviceRGB())
            gs.SetFillColor(APRYSE.ColorPt( rgb["red"],rgb["green"],rgb["blue"]))
            gs.SetFillOpacity(rgb["alpha"])

        return ele

    def _txt_to_rgb(self, txt):

        c = txt.replace("#", "")
        c = c.replace('"', "")

        if len(c) < 6:
            return { "red" : 1.0, "green" : 0.5, "blue" :0.5, "alpha" : 0.5 }

        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        a = 255
        if len(c) > 6:
            # if alpha supplied as well
            a = int(c[6:8], 16)

        # convert to floating point 0->1.0
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0
        a = a / 255.0

        return { "red" : r, "green" : g, "blue" :b, "alpha" : a }


    def newTextElements(self, src, builder, txt, style=None) -> list:

        style = style or {}

        LOGGER.debug(style)

        eles = []

        gs = src.GetGState()
        # fallbacks in case no style supplied
        font = gs.GetFont()
        font_size = gs.GetFontSize()

        if "font" in style:
            font = style["font"]
        if "font-size" in style:
            font_size = style["font-size"]

        LOGGER.debug(f"Using {style['font'].GetName()} @ {style['font-size']}")

        eles.append( builder.CreateTextRun(txt, font, font_size ) )

        return eles

    def drawBox(self, writer, builder, desc):

        box = builder.CreateRect(
            desc['x'], desc['y'],
            desc['width'],
            desc['height'])

        box.SetPathStroke(False)
        box.SetPathFill(True)

        rgb = desc['rgb']

        box.GetGState().SetFillColorSpace(APRYSE.ColorSpace.CreateDeviceRGB())
        box.GetGState().SetFillColor(APRYSE.ColorPt( rgb["red"],rgb["green"],rgb["blue"]))
        box.GetGState().SetFillOpacity(rgb["alpha"])

        self.writePlacedElement( writer, box )


    def newBox(self, obj, style=None) -> dict:

        desc = {}
        style = style or {}

        # obj is the demensions we get from OCR (needs DPI correction)
        # style is policy based
        LOGGER.info(f"Word @ {obj}")
        LOGGER.info(f"Style @ {style}")

        desc["width"] = 0
        desc["height"] = 0

        ocr_scale = 1.0

        if "dpi" in self.options:
            ocr_scale =  self.options["dpi"] / 72.0

        if "dpi" in style:
            ocr_scale =  style["dpi"] / 72.0

        if "box-width" in style:
            desc["width"] = style['box-width']

        if desc["width"] < 1.0 and 'length' in obj:
            # width is a fraction, so multiply if by overall word length
            desc["width"] = style['box-width'] * ( obj['length'] )

        # From experiment, the image is stored in the element at original
        # resolution, but the element bbox may be smaller.
        # OCR reports the word coords based on original resolution
        x_scale = 1.0
        y_scale = 1.0
        x_offset = 0.0
        y_offset = 0.0

        if "x-scale" in style:
            x_scale = style['x-scale']
        if "y-scale" in style:
            y_scale = style['y-scale']

        if "x-offset" in style:
            x_offset = style['x-offset']
        if "y-offset" in style:
            y_offset = style['y-offset']

        desc["width"] = desc["width"] * x_scale * ocr_scale

        if "box-height" in style:
            desc["height"] = style['box-height']


        if desc["height"] == 0:
            desc["height"] = obj["font-size"] * y_scale

        if desc["height"] < 1.0:
            desc["height"] = obj["font-size"] * y_scale * desc["height"]

        desc["x"] = ( ocr_scale * x_scale * obj['x'] ) + x_offset
        desc["y"] = ( ocr_scale * y_scale * obj['y'] ) + y_offset

        if "box-shape" in style:

            if style["box-shape"] == "overbar":
                desc["y"] = desc["y"] + ( obj["font-size"] * y_scale ) - style['box-height']
            if style["box-shape"] == "underbar":
                desc["y"] = desc["y"] - style['box-height'] - 1

        if "box-color" in style:
            desc["rgb"] = self._txt_to_rgb(style['box-color'])

        LOGGER.info(f"Box @ {desc}")

        return desc

    def extractTextFromImage(self, msg, out_filename="", out_dir="") -> str:
        """Returns JSON string containing nested objects
        {
            "Page": [
                {
                    "Para": [
                        {
                            "Line": [
                                {
                                    "Word": [
                                        {
                                            "font-size": 43,
                                            "length": 44,
                                            "orientation": "U",
                                            "text": "a2)",
                                            "x": 247,
                                            "y": 2217
                                        },
                                        ...
                                    ],
                                    "box" : [
                                    ]
                                },
                                ...
                            ],
                        }
                    ],
                    "dpi" : 96,
                    "num" : 1,
                    "origin": "BottomLeft"
                }
            ]
        }

        """


        ocr = ""

        def _process_page_as_ocr(page, file) -> str:
            """Using draw.Export() gives better word boundaries than
            Image(el.GetXObject())->ExportAsPng() but at the cost
            of a watermark in the intermediate image
            Since we only want the image to get word locations this is okay.

            However PDFDraw() takes the whole page. not just the
            image in the element.
            """

            drw = APRYSE.PDFDraw()
            drw.SetDPI(72)

            doc = APRYSE.PDFDoc()

            drw.Export(page, file.name)

            json = APRYSE.OCRModule.GetOCRJsonFromImage(
                doc, file.name, self._ocr_options)

            return json


        def _process_element_as_ocr(el, file) -> str:
            """Using draw.Export() gives better word boundaries than
            Image(el.GetXObject())->ExportAsPng() but at the cost
            of a watermark in the intermediate image
            Since we only want the image to get word locations this is okay.

            However PDFDraw() takes the whole page. not just the
            image in the element.
            """

            image = APRYSE.Image(el.GetXObject())

            image.ExportAsPng(file.name)

            doc = APRYSE.PDFDoc()

            json = APRYSE.OCRModule.GetOCRJsonFromImage(
                doc, file.name, self._ocr_options)

            return json


        if self.options.get("keep-files", False) is False:

            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:

                if self.options.get("ocr-whole-page", True) is True:
                    ocr = _process_page_as_ocr(msg.page, tmp)
                else:
                    ocr = _process_element_as_ocr(msg.element, tmp)

        else:

            base = PosixPath(self.read_file).name

            if out_dir:
                base = PosixPath(out_dir, base)
            if out_filename:
                base = PosixPath(out_filename)

            png = f"{base}.{msg.page_number}-{msg.ele_idx}.png"

            with open(png,"w") as tmp:

                LOGGER.info(f"Extracting intermediate image to {png}")

                if self.options.get("ocr-whole-page", True) is True:
                    ocr = _process_page_as_ocr(msg.page, tmp)
                else:
                    ocr = _process_element_as_ocr(msg.element, tmp)

        return ocr

    @property
    def devlog(self):
        return self._devlog

    @devlog.setter
    def devlog(self, value):
        self._devlog = value
