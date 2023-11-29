# EPUB support
# Copyright (c) 2023 Richard Offer. All rights reserved
#
# we have limited needs, and want to integrate into notify
# support like PDF handler, so handle EPUB manually (its a zip file)
#
import zipfile
from io import BytesIO

from bs4 import BeautifulSoup

from randeli import LOGGER

from .. import notify
from .base import BaseDocument

ELEMENTTYPES = {
}


class EPUB(BaseDocument):
    def __init__(self, options=None):
        super().__init__(options=options)

        self._document = None

    def finalise(self):
        pass

    def loadDocument(self, filename=""):
        super().loadDocument(filename)

        self.document = zipfile.ZipFile(filename)
        self.chapters = self.document.infolist()

        self.page_count = sum(1 if c.filename[:9] == "EPUB/text" else 0 for c in self.chapters)
        self.page_number = 0


    def processDocument(self, read_only=True):

        # EPUB don't have page numbers because of reflow
        # so count chapters as pages...
        self.page_number = 0

        self.builder = BytesIO()
        if read_only:
            self.writer = None
        else:
            self.writer = zipfile.ZipFile(self.builder, "w")

        for chap in self.chapters:

            if chap.filename[-6:] == ".xhtml":

                self.page_number += 1

                begin_page = notify.BeginPage(document=self.document,
                                         page=chap.filename,
                                         page_count=self.page_count,
                                         page_number=self.page_number,
                                         bbox=None)

                LOGGER.debug("Posting BeginPage notification")
                self.notificationCenter().raise_event("BeginPage", begin_page)

                self.processSection(chap, self.writer, None, self.page_number)

                end_page = notify.EndPage(document=self.document,
                                          writer=self.writer,
                                          builder=None)

                LOGGER.debug("Posting EndPage notification")
                self.notificationCenter().raise_event("EndPage", end_page)

            else:

                if self.writer:
                    with self.document.open(chap) as file:
                        if "content.opf" in chap.filename:

                            self.writer.writestr( chap, self.update_metadata(metadata=file.read()) )

                        else:
                            self.writer.writestr( chap, file.read() )


    def processSection(self, section, writer, builder, current_page):
        super().processPage(section, writer, builder, current_page)

        self.tree = None

        with self.document.open(section) as file:

            html = file.read()

            self.tree = BeautifulSoup(BytesIO(html), features="xml")

            ele_idx = 0
            for para in self.tree.find_all('p'):
                #for p in para.contents:
                element = notify.Element(document=self.document,
                                     reader=None,
                                     writer=self.writer,
                                     builder=self.tree,
                                     page=current_page,
                                     page_number=self.page_number,
                                     page_elements=[],#,
                                     bbox=None,
                                     ele_idx=ele_idx,
                                     ele_type=0,
                                     ele_type_str=para.name,
                                     element=para,
                                     )

                LOGGER.debug(f"Posting element notification")
                self.notificationCenter().raise_event("ProcessElement", element)

                ele_idx += 1

            if self.writer:
                self.writer.writestr( section, str(self.tree ) )

    def writeElement(self, element):
        pass

    def update_metadata(self, metadata=b""):

        tree = BeautifulSoup(BytesIO(metadata), features="xml")

        meta = tree.find('metadata')

        cont = tree.new_tag("dc:contributor")

        cont["opf:role"] = "oth"
        cont["opf:file-as"] = "github.com/badonhill-io/randeli"
        cont.string = f"Augmented using 'randeli' by Badon Hill Technologies Ltd. https://github.com/badonhill-io/randeli/"
        meta.append(cont)

        return str(tree)


    def saveDocument(self, filename="", write_into="", pdfa=False):


        if self.writer:
            self.writer.close()

            if write_into == "" and self.options['write-into']:
                write_into = self.options['write-into']

            super().saveDocument(filename=filename, in_dir=write_into)

            open(self.save_file, 'wb').write(self.builder.getbuffer())

            LOGGER.success(f"Saved augmented variant of {self.read_file} to {self.save_file.resolve()}")
