from pathlib import PosixPath

import EventNotifier


class BaseDocument:

    def __init__(self, options=None):
        self._options = options or {}

        self.nc_ = EventNotifier.Notifier(["OpenDocument", "BeginPage", "EndPage", "ProcessElement"])

    def notificationCenter(self) -> EventNotifier.Notifier :
        return self.nc_


    def register(self, event:str, callback):
        self.notificationCenter().subscribe( event, callback )


    def loadDocument(self, filename=""):
        self.read_file = filename

        self._document = None

    def processDocument(self):
        pass

    def processPage(self, reader, writer, builder, current_page):
        pass

    def saveDocument(self, filename="", in_dir=""):

        self.save_file = PosixPath(self.read_file).name

        if in_dir:
            self.save_file = PosixPath(in_dir, self.save_file)

        if filename:
            self.save_file = PosixPath(filename)

        if self.save_file == self.read_file:
            raise Exception("Output file cannot be the same as the input filename")

    def getImageDetails(self, ele = None) -> dict():
        return {}

    # Properties
    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value

    @property
    def document(self):
        return self._document

    @document.setter
    def document(self, value):
        self._document = value

    @property
    def read_file(self):
        return str(self._read_file)

    @read_file.setter
    def read_file(self, value):
        self._read_file = PosixPath(value)

    @property
    def save_file(self):
        return self._save_file_name

    @save_file.setter
    def save_file(self, value):
        self._save_file_name = value

    @property
    def document(self):
        return self._document

    @document.setter
    def document(self, value):
        self._document = value

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

    @property
    def page_count(self):
        return self._page_count

    @page_count.setter
    def page_count(self, value):
        self._page_count = value

    @property
    def page_number(self):
        return self._page_number

    @page_number.setter
    def page_number(self, value):
        self._page_number = value

    @property
    def ele_index(self):
        """Element index on page"""
        return self._ele_index

    @ele_index.setter
    def ele_index(self, value):
        self._ele_index = value
