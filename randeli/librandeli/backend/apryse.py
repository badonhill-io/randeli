
import logging
import math

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

class Apryse(BaseDocument):

    def __init__(self, options={}, log=log_name):
        super().__init__(options=options)

        self._document = None

        self._logger = logging.getLogger(log)
        self._devlog = logging.getLogger("d.devel")

        if "apryse-token" not in self.options or self.options["apryse-token"] == "":
            self.logger.fatal("Missing Apryse API key")
            raise Exception("Missing Apryse API key")

        APRYSE.PDFNet.Initialize( self.options["apryse-token"] )


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

            end_page = notify.EndPage(document=self.document)

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
    def saveDocument(self, filename="", in_dir=""):
        # standardize generation of save pathname
        super().saveDocument(filename=filename, in_dir=in_dir)

        self.logger.info(f"Saving to {self.save_file}")

        info = self.document.GetDocInfo()
        producer = info.GetProducer()
        info.SetProducer(f"{producer} - Updated by 'randeli' from Badon Hill Technologies Ltd.")
        d = APRYSE.Date()
        d.SetCurrentTime()
        info.SetModDate( d )

        self.document.Save(self.save_file, APRYSE.SDFDoc.e_remove_unused )



    def getImageDetails(self, ele) -> dict():
        h = ele.GetImageHeight()
        w = ele.GetImageWidth()
        return { "width" : w, "height" : h }

    def getTextDetails(self, ele) -> dict():
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
        }

    def updateTextInElement(self, writer, ele, txt, style={}) -> object:
        """TODO
        this currently only handles UTF-8 (i.e. pdflatex), it does not
        handle xelatex generated PDFs - the font mapping is different
        (type1 vs CID fonts?)
        """

        self.devlog.info(style)

        gs = ele.GetGState()

        head_len = len(txt)
        td = ele.GetTextData()
        ele.SetTextData(td[:head_len], len(td[:head_len]) )


        if "font-path" in style and "font-size" in style:
            self.logger.debug(f"Using {style['font-path']}")
            fnt = APRYSE.Font.CreateTrueTypeFont(
                    self.document.GetSDFDoc(),
                    style["font-path"] )

            gs.SetFont(fnt, style['font-size'])

        else:
            self.logger.warn("No font specified in style")

        if "text-color" in style and len(style['text-color']) > 2:
            r = style["text-color"][0]
            g = style["text-color"][1]
            b = style["text-color"][2]

            # if alpha supplied as well
            if len(style['text-color']) > 3:
                alpha = style["text-color"][3]

            gs.SetFillColorSpace(APRYSE.ColorSpace.CreateDeviceRGB())
            gs.SetFillColor(APRYSE.ColorPt(r,g,b))
        
        return ele

    def newTextElements(self, src, builder, txt, style={}) -> list:

        self.devlog.info(style)

        eles = []

        gs = src.GetGState()

        if "font" in style:
            font = style["font"]
        if "font-size" in style:
            font_size = 12 #style["font-size"]

        #eles.append( builder.CreateTextBegin(font, font_size) )

        eles.append( builder.CreateTextRun(txt, font, font_size ) )

        #eles.append( builder.CreateTextEnd( ) )

        return eles


    @property
    def devlog(self):
        return self._devlog

    @devlog.setter
    def devlog(self, value):
        self._devlog = value 
