
import logging
import logging.config
import math
import tempfile
import json

import apryse_sdk as APRYSE

from . import BaseDocument
from .. import notify 
from .. trace import tracer as FTRACE 

log_name = "r.l.b.apryse"

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

LOGGER = logging.getLogger(log_name)
DEVLOG = logging.getLogger("d.devel")

class Apryse(BaseDocument):

    def __init__(self, options={}, log=log_name):
        super().__init__(options=options)

        self._document = None

        self.logger = logging.getLogger(log)
        self.devlog = logging.getLogger("d.devel")

        self._ocr_options = None

        if "apryse-token" not in self.options or self.options["apryse-token"] == "":
            self.logger.fatal("Missing Apryse API key")
            raise Exception("Missing Apryse API key")

        APRYSE.PDFNet.Initialize( self.options["apryse-token"] )

        try:
            if self.options.get("apryse-ocr", False) is True:

                self._ocr_options = APRYSE.OCROptions()
                self._ocr_options.SetUsePDFPageCoords(True);
                #self._ocr_options.AddDPI(96);

                if self.options.get("apryse-libdir", ""):

                    self._ocrdir = self.options["apryse-libdir"]
                    
                    APRYSE.PDFNet.AddResourceSearchPath(self._ocrdir)
                    self.logger.info(f"OCR has been enabled")
                    self.logger.error(f" libdir = {self._ocrdir}")

                else:
                    self.logger.error("OCR has been requested, but no ocr.libdir is set")

        except Exception as e:
            self.logger.error(str(e))


    def finalise(self):

        self.document.Close()

        APRYSE.PDFNet.Terminate()


    @FTRACE
    def loadDocument(self, filename=""):
        super().loadDocument(filename)

        self.document = APRYSE.PDFDoc( self.read_file )

        self.document.InitSecurityHandler()

        self.page_count = self.document.GetPageCount()
        self.page_number = 0

        call_data = notify.OpenDocument(document=self.document,
                                        filename=filename,
                                        page_count=self.document.GetPageCount())

        self.logger.trace("Posting OpenDocument notification")

        self.notificationCenter().raise_event("OpenDocument", call_data)

        self.logger.trace("Posted OpenDocument notification")

    @FTRACE
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

            begin_page = notify.BeginPage(document=self.document,
                                         page_count=self.page_count,
                                         page_number=self.page_number)

            self.logger.trace("Posting BeginPage notification")
            self.notificationCenter().raise_event("BeginPage", begin_page)

            # reset to zero on each page
            self.ele_index = 0

            self.processPage(reader, writer, builder)

            end_page = notify.EndPage(document=self.document, writer=writer, builder=builder)

            self.logger.trace("Posting EndPage notification")
            self.notificationCenter().raise_event("EndPage", end_page)

            reader.End()
            if writer:
                writer.End()

            itr.Next()

    @FTRACE
    def processPage(self, reader, writer, builder):
        super().processPage()

        page_elements = []

        ele = reader.Next()

        while ele != None:

            self.ele_index += 1

            page_elements.append( ele.GetType() )

            element = notify.Element(document=self.document,
                                     reader=reader,
                                     writer=writer,
                                     builder=builder,
                                     page_number=self.page_number,
                                     page_elements=page_elements,
                                     ele_idx=self.ele_index,
                                     ele_type=ele.GetType(),
                                     ele_type_str=ELEMENTTYPES[ele.GetType()],
                                     element=ele,
                                     )

            self.logger.trace("Posting Element notification")
            self.notificationCenter().raise_event("ProcessElement", element)

            ele = reader.Next()

    @FTRACE
    def writeElement(self, writer, element):
        if writer and element:
            writer.WriteElement(element)

    @FTRACE
    def writePlacedElement(self, writer, element):
        if writer and element:
            writer.WritePlacedElement(element)
            writer.Flush()

    @FTRACE
    def saveDocument(self, filename="", in_dir=""):
        # standardize generation of save pathname
        super().saveDocument(filename=filename, in_dir=in_dir)

        self.logger.info(f"Saving to {self.save_file}")

        info = self.document.GetDocInfo()
        producer = info.GetProducer()
        info.SetProducer(f"{producer} - Augmented using 'randeli' by Badon Hill Technologies Ltd.")
        d = APRYSE.Date()
        d.SetCurrentTime()
        info.SetModDate( d )

        self.document.Save(self.save_file, APRYSE.SDFDoc.e_remove_unused )



    @FTRACE
    def getImageDetails(self, ele) -> dict():
        rect = ele.GetBBox()
        h = ele.GetImageHeight()
        w = ele.GetImageWidth()
        return {
            "x" : int(rect.GetX1()),
            "y" : int(rect.GetY1()),
            "width" : int(rect.GetX2() - rect.GetX1()) ,
            "height" : int(rect.GetY2() - rect.GetY1())
        }

    @FTRACE
    def getTextDetails(self, ele) -> dict():
        rect = ele.GetBBox()
        txt = ele.GetTextString()
        fnt = ele.GetGState().GetFont()
        font_family = fnt.GetFamilyName() or fnt.GetName()
        name = fnt.GetName() or fnt.GetFamilyName()
        sz = ele.GetGState().GetFontSize()

        desc = fnt.GetDescriptor()
        italic = fnt.IsItalic()

        if desc:
            itr = desc.GetDictIterator();
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
            "x" : rect.GetX1(),
            "y" : rect.GetY1(),
            "length" : rect.GetX2() - rect.GetX1() ,
            "height" : rect.GetY2() - rect.GetY1(),
        }

    @FTRACE
    def updateTextInElement(self, writer, ele, txt, style={}) -> object:
        """TODO
        this currently only handles UTF-8 (i.e. pdflatex), it does not
        handle xelatex generated PDFs - the font mapping is different
        (type1 vs CID fonts?)
        """

        gs = ele.GetGState()

        head_len = len(txt)
        td = ele.GetTextData()
        ele.SetTextData(td[:head_len], len(td[:head_len]) )


        if "font-path" in style and "font-size" in style:
            if style['font-path'] and style['font-size'] > 0.0:
                self.logger.debug(f"Using {style['font-path']}")
                fnt = APRYSE.Font.CreateTrueTypeFont(
                    self.document.GetSDFDoc(),
                    style["font-path"] )

                self.devlog.debug(f"Using {style['font-path']} @ {style['font-size']} as strong")
                gs.SetFont(fnt, style['font-size'])

            else:
                self.logger.detail("No font specified in style")

        if "text-color" in style and len(style['text-color']) > 6:
            # text-color is #rrggbbaa string, convert to 0.0->1.0
            rgb = self._txt_to_rgb(style['text-color'])

            gs.SetFillColorSpace(APRYSE.ColorSpace.CreateDeviceRGB())
            gs.SetFillColor(APRYSE.ColorPt(
                rgb["red"],rgb["green"],rgb["blue"]))
        
        return ele

    def _txt_to_rgb(self, txt):

        c = txt.replace("#", "")

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


    @FTRACE
    def newTextElements(self, src, builder, txt, style={}) -> list:

        self.devlog.info(style)

        eles = []

        gs = src.GetGState()
        # fallbacks in case no style supplied
        font = gs.GetFont()
        font_size = gs.GetFontSize()

        if "font" in style:
            font = style["font"]
        if "font-size" in style:
            font_size = style["font-size"]

        self.devlog.debug(f"Using {style['font']} @ {style['font-size']}")

        #eles.append( builder.CreateTextBegin(font, font_size) )

        eles.append( builder.CreateTextRun(txt, font, font_size ) )

        #eles.append( builder.CreateTextEnd( ) )

        return eles

    @FTRACE
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


    @FTRACE
    def newBox(self, obj, style={}) -> dict:

        desc = {}

        desc["height"] = 0

        if "box-height" in style:
            desc["height"] = style['box-height']

        if desc["height"] == 0:
            desc["height"] = obj["font-size"]

        desc["width"] = 0

        if "box-width" in style:
            desc["width"] = style['box-width']

        if desc["width"] < 1.0 and 'length' in obj:
            # width is a fraction, so multiply if by overall word length
            desc["width"] = style['box-width'] * ( obj['length'] )

        desc["x"] = ( style['box-x-scale'] * obj['x'] ) + style['box-x-offset'] 
        desc["y"] = ( style['box-y-scale'] * obj['y'] ) + style['box-y-offset'] 

        if "box-color" in style:
            desc["rgb"] = self._txt_to_rgb(style['box-color'])

        return desc

    @FTRACE
    def extractTextFromImage(self, el) -> dict():
        """Returns nested dictionary
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

        image = APRYSE.Image(el.GetXObject())

        doc = APRYSE.PDFDoc()

        ocr = {}

        #with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        with open("fred.png","w") as tmp:

            image.ExportAsPng(tmp.name)

            txt = APRYSE.OCRModule.GetOCRJsonFromImage(
                doc, tmp.name, self._ocr_options)

            ocr = json.loads(txt)

        return ocr['Page'][0]['Para']

    @property
    def devlog(self):
        return self._devlog

    @devlog.setter
    def devlog(self, value):
        self._devlog = value 
